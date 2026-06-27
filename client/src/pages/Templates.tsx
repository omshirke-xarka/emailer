import { useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import TemplateEditor from '../components/TemplateEditor';
import { getTemplates, createTemplate, updateTemplate, deleteTemplate } from '../api/client';
import type { Template } from '../types';

export default function Templates() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [editing, setEditing] = useState<Template | null>(null);
  const [creating, setCreating] = useState(false);

  const fetchTemplates = async () => {
    try {
      const data = await getTemplates();
      setTemplates(Array.isArray(data) ? data : []);
    } catch {
      toast.error('Failed to load templates');
    }
  };

  useEffect(() => {
    fetchTemplates();
  }, []);

  const handleSave = async (data: { name: string; subject: string; body_html: string; preview_text: string }) => {
    try {
      if (editing) {
        await updateTemplate(editing.id, data);
        toast.success('Template updated');
      } else {
        await createTemplate(data);
        toast.success('Template created');
      }
      setEditing(null);
      setCreating(false);
      fetchTemplates();
    } catch {
      toast.error('Failed to save template');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteTemplate(id);
      toast.success('Template deleted');
      fetchTemplates();
    } catch {
      toast.error('Failed to delete template');
    }
  };

  if (creating || editing) {
    return (
      <div>
        <h2 className="text-2xl font-bold mb-4">{editing ? 'Edit Template' : 'New Template'}</h2>
        <TemplateEditor
          initialName={editing?.name}
          initialSubject={editing?.subject}
          initialBody={editing?.body_html}
          initialPreviewText={editing?.preview_text || ''}
          onSave={handleSave}
          onCancel={() => { setCreating(false); setEditing(null); }}
        />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">Templates</h2>
        <button
          className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm"
          onClick={() => setCreating(true)}
        >
          New Template
        </button>
      </div>

      {templates.length === 0 ? (
        <p className="text-gray-500 text-sm">No templates yet. Create one to get started.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((t) => (
            <div key={t.id} className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold text-lg">{t.name}</h3>
              <p className="text-sm text-gray-500 mt-1">Subject: {t.subject}</p>
              <div className="mt-3 flex gap-2">
                <button
                  className="px-3 py-1 text-sm border rounded hover:bg-gray-50"
                  onClick={() => setEditing(t)}
                >
                  Edit
                </button>
                <button
                  className="px-3 py-1 text-sm text-red-600 border border-red-200 rounded hover:bg-red-50"
                  onClick={() => handleDelete(t.id)}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
