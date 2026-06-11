import { useCallback, useState, useEffect } from 'react';
import toast from 'react-hot-toast';
import { getEmails, getEmailDetail, retryEmail } from '../api/client';
import type { Email, EmailDetail } from '../types';

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString();
}

function pct(n: number, total: number) {
  if (total === 0) return '0%';
  return `${Math.round((n / total) * 100)}%`;
}

export default function EmailLog() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState<EmailDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const loadEmails = useCallback(() => {
    setLoading(true);
    return getEmails()
      .then(setEmails)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadEmails();
  }, [loadEmails]);

  const viewDetail = async (id: string) => {
    setLoadingDetail(true);
    try {
      const data = await getEmailDetail(id);
      setDetail(data);
    } catch {
      // ignore
    } finally {
      setLoadingDetail(false);
    }
  };

  const canRetry = (email: Email) => email.status === 'failed' || email.status === 'partial';

  const handleRetry = async (email: Email, event?: React.MouseEvent) => {
    event?.stopPropagation();
    setRetryingId(email.id);

    try {
      const result = await retryEmail(email.id);
      if (result.sent > 0 && result.failed === 0) {
        toast.success(`Retry sent to ${result.sent} recipient${result.sent === 1 ? '' : 's'}`);
      } else if (result.sent > 0) {
        toast.error(`Retry partially sent: ${result.sent} sent, ${result.failed} failed`);
      } else {
        toast.error(`Retry failed for ${result.failed} recipient${result.failed === 1 ? '' : 's'}`);
      }

      await loadEmails();
      if (detail?.email.id === email.id) {
        const updatedDetail = await getEmailDetail(email.id);
        setDetail(updatedDetail);
      }
    } catch {
      toast.error('Failed to retry email');
    } finally {
      setRetryingId(null);
    }
  };

  if (detail) {
    const { email, recipients } = detail;
    return (
      <div>
        <button
          className="text-indigo-600 hover:underline text-sm mb-4"
          onClick={() => setDetail(null)}
        >
          &larr; Back to Email Log
        </button>
        <div className="mb-2 flex items-center justify-between gap-4">
          <h2 className="text-2xl font-bold">{email.subject}</h2>
          {canRetry(email) && (
            <button
              className="px-4 py-2 bg-indigo-600 text-white rounded text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
              onClick={() => handleRetry(email)}
              disabled={retryingId === email.id}
            >
              {retryingId === email.id ? 'Retrying...' : 'Retry Failed'}
            </button>
          )}
        </div>
        <div className="flex gap-6 text-sm text-gray-500 mb-6">
          <span>Sent: {formatDate(email.sent_at)}</span>
          <span>Status: <span className={`font-medium ${email.status === 'sent' ? 'text-green-600' : email.status === 'partial' ? 'text-amber-600' : 'text-red-600'}`}>{email.status}</span></span>
          <span>Failed attempts: <span className="font-medium text-red-600">{email.failure_count}</span></span>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <p className="text-3xl font-bold text-indigo-600">{email.total_recipients}</p>
            <p className="text-sm text-gray-500">Recipients</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <p className="text-3xl font-bold text-green-600">{email.total_opens}</p>
            <p className="text-sm text-gray-500">Opened ({pct(email.total_opens, email.total_recipients)})</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4 text-center">
            <p className="text-3xl font-bold text-blue-600">{email.total_clicks}</p>
            <p className="text-sm text-gray-500">Clicked ({pct(email.total_clicks, email.total_recipients)})</p>
          </div>
        </div>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Name</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Email</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Delivery</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Failures</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Opened</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Opens</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Clicked</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Clicks</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {recipients.map((r) => (
                <tr key={r.tracking_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">{r.name}</td>
                  <td className="px-4 py-3 text-gray-500">{r.email}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      r.send_status === 'sent' ? 'bg-green-100 text-green-700' :
                      r.send_status === 'failed' ? 'bg-red-100 text-red-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {r.send_status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-red-600">{r.failure_count}</td>
                  <td className="px-4 py-3">
                    {r.opened_at ? (
                      <span className="text-green-600">{formatDate(r.opened_at)}</span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">{r.open_count}</td>
                  <td className="px-4 py-3">
                    {r.clicked_at ? (
                      <span className="text-blue-600">{formatDate(r.clicked_at)}</span>
                    ) : (
                      <span className="text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">{r.click_count}</td>
                </tr>
              ))}
              {recipients.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-4 py-8 text-center text-gray-400">No recipients found</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Email Log</h2>

      {loading ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : emails.length === 0 ? (
        <p className="text-gray-500 text-sm">No emails sent yet.</p>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Subject</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Recipients</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Opens</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Clicks</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="text-center px-4 py-3 font-medium text-gray-600">Failures</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Sent</th>
                <th className="text-right px-4 py-3 font-medium text-gray-600">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {emails.map((e) => (
                <tr
                  key={e.id}
                  className="hover:bg-gray-50 cursor-pointer"
                  onClick={() => viewDetail(e.id)}
                >
                  <td className="px-4 py-3 font-medium text-indigo-600 hover:underline">{e.subject}</td>
                  <td className="px-4 py-3 text-center">{e.total_recipients}</td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-green-600">{e.total_opens}</span>
                    <span className="text-gray-400 ml-1">({pct(e.total_opens, e.total_recipients)})</span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className="text-blue-600">{e.total_clicks}</span>
                    <span className="text-gray-400 ml-1">({pct(e.total_clicks, e.total_recipients)})</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      e.status === 'sent' ? 'bg-green-100 text-green-700' :
                      e.status === 'partial' ? 'bg-amber-100 text-amber-700' :
                      'bg-red-100 text-red-700'
                    }`}>
                      {e.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center text-red-600">{e.failure_count}</td>
                  <td className="px-4 py-3 text-gray-500">{formatDate(e.sent_at)}</td>
                  <td className="px-4 py-3 text-right">
                    {canRetry(e) && (
                      <button
                        className="px-3 py-1.5 bg-indigo-600 text-white rounded text-xs font-medium hover:bg-indigo-700 disabled:opacity-50"
                        onClick={(event) => handleRetry(e, event)}
                        disabled={retryingId === e.id}
                      >
                        {retryingId === e.id ? 'Retrying...' : 'Retry'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loadingDetail && (
        <div className="fixed inset-0 bg-black/20 flex items-center justify-center">
          <div className="bg-white rounded-lg shadow-lg px-6 py-4">Loading details...</div>
        </div>
      )}
    </div>
  );
}
