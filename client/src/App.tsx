import { useEffect, useState } from 'react';
import { Routes, Route, NavLink } from 'react-router-dom';
import toast from 'react-hot-toast';
import Dashboard from './pages/Dashboard';
import Templates from './pages/Templates';
import ComposeEmail from './pages/ComposeEmail';
import EmailLog from './pages/EmailLog';
import Schedules from './pages/Schedules';
import { getEmailProvider, updateEmailProvider } from './api/client';
import type { EmailProvider } from './types';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/templates', label: 'Templates' },
  { to: '/emails', label: 'Email Log' },
  { to: '/schedules', label: 'Schedules' },
];

function App() {
  const [emailProvider, setEmailProvider] = useState<EmailProvider>('aws');
  const [providerLoading, setProviderLoading] = useState(false);

  useEffect(() => {
    getEmailProvider()
      .then((res) => setEmailProvider(res.provider))
      .catch(() => {});
  }, []);

  const handleProviderToggle = async () => {
    const nextProvider: EmailProvider = emailProvider === 'aws' ? 'resend' : 'aws';
    const previousProvider = emailProvider;
    setEmailProvider(nextProvider);
    setProviderLoading(true);

    try {
      const res = await updateEmailProvider(nextProvider);
      setEmailProvider(res.provider);
      toast.success(`Email provider changed to ${res.provider === 'aws' ? 'AWS' : 'Resend'}`);
    } catch {
      setEmailProvider(previousProvider);
      toast.error('Failed to switch email provider');
    } finally {
      setProviderLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <nav className="bg-white border-b border-gray-200 px-6 py-3">
        <div className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-6">
          <div className="flex min-w-0 gap-4">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
          <h1 className="text-xl font-bold text-indigo-600">Emailer</h1>
          <button
            type="button"
            onClick={handleProviderToggle}
            disabled={providerLoading}
            className="relative flex h-9 w-36 shrink-0 justify-self-end items-center rounded-full border border-gray-300 bg-gray-100 p-1 text-xs font-semibold text-gray-500 transition disabled:opacity-60"
            aria-label="Switch email provider"
          >
            <span
              className={`absolute left-1 top-1 h-7 w-16 rounded-full bg-indigo-600 shadow-sm transition-transform ${
                emailProvider === 'resend' ? 'translate-x-[4.25rem]' : 'translate-x-0'
              }`}
            />
            <span className={`relative z-10 flex-1 text-center transition-colors ${emailProvider === 'aws' ? 'text-white' : 'text-gray-600'}`}>
              AWS
            </span>
            <span className={`relative z-10 flex-1 text-center transition-colors ${emailProvider === 'resend' ? 'text-white' : 'text-gray-600'}`}>
              Resend
            </span>
          </button>
        </div>
      </nav>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/templates" element={<Templates />} />
          <Route path="/compose" element={<ComposeEmail />} />
          <Route path="/emails" element={<EmailLog />} />
          <Route path="/schedules" element={<Schedules />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
