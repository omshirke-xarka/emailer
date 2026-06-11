import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import TemplateSelector from '../components/TemplateSelector';
import EmailPreview from '../components/EmailPreview';
import ScheduleModal from '../components/ScheduleModal';
import {
  getTemplates,
  getContacts,
  getContactsForList,
  sendEmail,
  previewEmail,
  scheduleEmail,
} from '../api/client';
import type { Template, Contact, DynamicContact } from '../types';

export default function ComposeEmail() {
  const location = useLocation();
  const navigate = useNavigate();
  const contactIds: number[] = location.state?.contactIds || [];
  const rawListId: string | null = location.state?.listId || null;
  const listId: string | null = rawListId === 'all' ? null : rawListId;

  const [templates, setTemplates] = useState<Template[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [dynamicContacts, setDynamicContacts] = useState<DynamicContact[]>([]);
  const [dynamicEmailCol, setDynamicEmailCol] = useState<string>('email');
  const [dynamicNameCol, setDynamicNameCol] = useState<string | null>(null);
  const [subject, setSubject] = useState('');
  const [previewText, setPreviewText] = useState('');
  const [bodyHtml, setBodyHtml] = useState('');
  const [previewHtml, setPreviewHtml] = useState('');
  const [sending, setSending] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);

  useEffect(() => {
    getTemplates().then(setTemplates).catch(() => {});
    if (contactIds.length > 0) {
      if (listId) {
        // Fetch contacts from the specific list
        getContactsForList(listId, { limit: '0' }).then((res) => {
          const idSet = new Set(contactIds);
          setDynamicContacts(res.data.filter((c) => idSet.has(c.id)));
          const cols = res.columns || [];
          const emailCol = cols.find((h) => h.toLowerCase().includes('email')) || cols[0] || 'email';
          const nameCol = cols.find((h) => /^(username|name|first.?name|full.?name)$/i.test(h)) || null;
          setDynamicEmailCol(emailCol);
          setDynamicNameCol(nameCol);
        }).catch(() => {});
      } else {
        getContacts({ limit: '0' }).then((res) => {
          setContacts(res.data.filter((c) => contactIds.includes(c.id)));
        }).catch(() => {});
      }
    }
  }, []);

  useEffect(() => {
    if (bodyHtml) {
      previewEmail(bodyHtml, contactIds[0], listId || undefined).then((r) => setPreviewHtml(r.html)).catch(() => {});
    } else {
      setPreviewHtml('');
    }
  }, [bodyHtml]);

  const handleTemplateSelect = (template: Template | null) => {
    setSelectedTemplate(template);
    if (template) {
      setSubject(template.subject);
      setBodyHtml(template.body_html);
      setPreviewText(template.preview_text || '');
    }
  };

  const handleSend = async () => {
    if (!subject || !bodyHtml || contactIds.length === 0) {
      toast.error('Subject, body, and recipients are required');
      return;
    }
    setSending(true);
    try {
      const result = await sendEmail({
        contactIds,
        subject,
        bodyHtml,
        templateId: selectedTemplate?.id,
        previewText: previewText || undefined,
        listId: listId || undefined,
      });

      if (result.sent > 0 && result.failed === 0) {
        toast.success(`Email sent to ${result.sent} recipient${result.sent === 1 ? '' : 's'}`);
        navigate('/');
      } else if (result.sent > 0) {
        toast.error(`Email partially sent: ${result.sent} sent, ${result.failed} failed`);
      } else {
        toast.error(`Email failed for ${result.failed} recipient${result.failed === 1 ? '' : 's'}`);
      }
    } catch {
      toast.error('Failed to send');
    } finally {
      setSending(false);
    }
  };

  const handleSchedule = async (scheduledAt: string) => {
    if (!subject || !bodyHtml || contactIds.length === 0) {
      toast.error('Subject, body, and recipients are required');
      return;
    }
    setShowScheduleModal(false);
    setSending(true);
    try {
      await scheduleEmail({
        contactIds,
        subject,
        bodyHtml,
        templateId: selectedTemplate?.id,
        previewText: previewText || undefined,
        scheduledAt,
        listId: listId || undefined,
      });
      toast.success('Email scheduled!');
      navigate('/schedules');
    } catch {
      toast.error('Failed to schedule');
    } finally {
      setSending(false);
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Compose Email</h2>

      <div className="mb-4 bg-white rounded-lg shadow p-4">
        <h3 className="text-sm font-medium text-gray-600 mb-2">
          Recipients ({listId ? dynamicContacts.length : contacts.length})
        </h3>
        <div className="flex flex-wrap gap-2">
          {listId ? (
            dynamicContacts.map((c) => {
              const email = String(c[dynamicEmailCol] ?? '');
              const name = dynamicNameCol ? String(c[dynamicNameCol] ?? '') : '';
              return (
                <span key={c.id} className="bg-gray-100 px-3 py-1 rounded-full text-sm">
                  {name ? `${name} <${email}>` : email}
                </span>
              );
            })
          ) : (
            contacts.map((c) => (
              <span key={c.id} className="bg-gray-100 px-3 py-1 rounded-full text-sm">
                {c.username} &lt;{c.email}&gt;
              </span>
            ))
          )}
          {contacts.length === 0 && dynamicContacts.length === 0 && (
            <p className="text-sm text-gray-400">No recipients selected. Go back to Dashboard to select contacts.</p>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Template</label>
            <TemplateSelector
              templates={templates}
              selectedId={selectedTemplate?.id ?? null}
              onSelect={handleTemplateSelect}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Subject</label>
            <input
              className="w-full px-3 py-2 border rounded"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Email subject..."
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Preview Text</label>
            <input
              className="w-full px-3 py-2 border rounded"
              value={previewText}
              onChange={(e) => setPreviewText(e.target.value)}
              placeholder="Text shown in inbox preview instead of email body..."
            />
            <p className="text-xs text-gray-400 mt-1">This text appears in the inbox preview. It won't be visible in the email itself.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Body (HTML)</label>
            <textarea
              className="w-full px-3 py-2 border rounded font-mono text-sm h-64"
              value={bodyHtml}
              onChange={(e) => setBodyHtml(e.target.value)}
              placeholder="<h1>Hello {{username}}</h1>"
            />
          </div>
          <div className="flex gap-3">
            <button
              className="px-6 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
              onClick={handleSend}
              disabled={sending || contactIds.length === 0}
            >
              {sending ? 'Sending...' : 'Send Now'}
            </button>
            <button
              className="px-6 py-2 border border-indigo-600 text-indigo-600 rounded hover:bg-indigo-50 disabled:opacity-50"
              onClick={() => setShowScheduleModal(true)}
              disabled={sending || contactIds.length === 0}
            >
              Schedule
            </button>
          </div>
        </div>
        <div>
          <EmailPreview html={previewHtml} />
        </div>
      </div>

      {showScheduleModal && (
        <ScheduleModal
          onSchedule={handleSchedule}
          onCancel={() => setShowScheduleModal(false)}
        />
      )}
    </div>
  );
}
