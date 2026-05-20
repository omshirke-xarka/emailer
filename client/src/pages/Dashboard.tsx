import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import ContactTable from '../components/ContactTable';
import DynamicContactTable from '../components/DynamicContactTable';
import FilterBar from '../components/FilterBar';
import {
  getContacts,
  getFilterOptions,
  uploadContactsCsv,
  getContactLists,
  createContactList,
  getContactsForList,
  uploadCsvToList,
  deleteContactList,
} from '../api/client';
import type { Contact, ContactList, DynamicContact } from '../types';

function MetricCards({ contacts }: { contacts: Contact[] }) {
  const stats = useMemo(() => {
    const total = contacts.length;
    const subscribed = contacts.filter((c) => c.subscribed === 'Yes').length;
    const plusPlan = contacts.filter((c) => c.plan === 'Plus').length;
    const today = new Date().toISOString().slice(0, 10);
    const activeToday = contacts.filter((c) => c.last_login?.startsWith(today)).length;
    return [
      { label: 'Total Contacts', value: total, color: 'bg-blue-50 text-blue-700 border-blue-200' },
      { label: 'Subscribed', value: subscribed, color: 'bg-green-50 text-green-700 border-green-200' },
      { label: 'Plus Plan', value: plusPlan, color: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
      { label: 'Active Today', value: activeToday, color: 'bg-amber-50 text-amber-700 border-amber-200' },
    ];
  }, [contacts]);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      {stats.map((s) => (
        <div key={s.label} className={`rounded-lg border p-4 ${s.color}`}>
          <p className="text-xs font-semibold uppercase tracking-wide opacity-75">{s.label}</p>
          <p className="text-2xl font-bold mt-1">{s.value.toLocaleString()}</p>
        </div>
      ))}
    </div>
  );
}

function NewListModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (list: ContactList) => void;
}) {
  const [name, setName] = useState('');
  const [creating, setCreating] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);

  if (!open) return null;

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error('Please enter a name for the contact list');
      return;
    }
    if (!file) {
      toast.error('Please select a CSV file');
      return;
    }
    setCreating(true);
    try {
      const text = await file.text();
      const list = await createContactList(name.trim(), text);
      toast.success(`Created "${list.name}" with ${list.contact_count} contacts`);
      onCreated(list);
      setName('');
      setFile(null);
      onClose();
    } catch {
      toast.error('Failed to create contact list');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">New Contact List</h3>

        <label className="block text-sm font-medium text-gray-700 mb-1">List Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Marketing Leads"
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          autoFocus
        />

        <label className="block text-sm font-medium text-gray-700 mb-1">CSV File</label>
        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="w-full border-2 border-dashed border-gray-300 rounded px-3 py-4 text-sm text-gray-500 hover:border-indigo-400 hover:text-indigo-600 transition mb-4"
        >
          {file ? file.name : 'Click to select a CSV file'}
        </button>

        <div className="flex justify-end gap-3">
          <button
            onClick={() => { setName(''); setFile(null); onClose(); }}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            disabled={creating}
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={creating}
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm disabled:opacity-50"
          >
            {creating ? 'Creating...' : 'Create List'}
          </button>
        </div>
      </div>
    </div>
  );
}

function DeleteListModal({
  open,
  listName,
  onClose,
  onConfirm,
}: {
  open: boolean;
  listName: string;
  onClose: () => void;
  onConfirm: () => void;
}) {
  const [input, setInput] = useState('');
  const [deleting, setDeleting] = useState(false);

  if (!open) return null;

  const handleConfirm = async () => {
    if (input !== 'DELETE') return;
    setDeleting(true);
    await onConfirm();
    setDeleting(false);
    setInput('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-2 text-red-600">Delete "{listName}"</h3>
        <p className="text-sm text-gray-600 mb-4">
          To confirm deleting the list, type <span className="font-bold">DELETE</span> below.
        </p>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="DELETE"
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-red-500"
          autoFocus
          onKeyDown={(e) => e.key === 'Enter' && handleConfirm()}
        />
        <div className="flex justify-end gap-3">
          <button
            onClick={() => { setInput(''); onClose(); }}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            disabled={deleting}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            disabled={input !== 'DELETE' || deleting}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 text-sm disabled:opacity-50"
          >
            {deleting ? 'Deleting...' : 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [dynamicContacts, setDynamicContacts] = useState<DynamicContact[]>([]);
  const [dynamicColumns, setDynamicColumns] = useState<string[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [subscribed, setSubscribed] = useState('');
  const [plan, setPlan] = useState('');
  const [planOptions, setPlanOptions] = useState<string[]>([]);
  const [subscribedOptions, setSubscribedOptions] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Contact lists
  const [contactLists, setContactLists] = useState<ContactList[]>([]);
  const [activeList, setActiveList] = useState<string | null>(null); // null = default "All Contacts"
  const [showNewListModal, setShowNewListModal] = useState(false);

  // Debounce search input by 300ms
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Load contact lists
  useEffect(() => {
    getContactLists().then(setContactLists).catch(() => {});
  }, []);

  useEffect(() => {
    if (activeList === null) {
      getFilterOptions()
        .then((opts) => {
          setPlanOptions(opts.plans);
          setSubscribedOptions(opts.subscribedValues);
        })
        .catch(() => {});
    }
  }, [activeList]);

  const fetchContacts = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (debouncedSearch) params.search = debouncedSearch;
      params.limit = '0';

      if (activeList) {
        const res = await getContactsForList(activeList, params);
        setDynamicContacts(res.data);
        setDynamicColumns(res.columns || []);
        setContacts([]);
      } else {
        if (subscribed) params.subscribed = subscribed;
        if (plan) params.plan = plan;
        const res = await getContacts(params);
        setContacts(res.data);
        setDynamicContacts([]);
        setDynamicColumns([]);
      }
    } catch {
      toast.error('Failed to load contacts');
    }
  }, [debouncedSearch, subscribed, plan, activeList]);

  // Clear selection when dropdown filters change
  useEffect(() => {
    setSelectedIds(new Set());
  }, [subscribed, plan]);

  // Clear selection and filters when switching lists
  useEffect(() => {
    setSelectedIds(new Set());
    setSearch('');
    setDebouncedSearch('');
    setSubscribed('');
    setPlan('');
  }, [activeList]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  const handleCompose = () => {
    const ids = Array.from(selectedIds);
    navigate('/compose', { state: { contactIds: ids, listId: activeList } });
  };

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.endsWith('.csv')) {
      toast.error('Please select a CSV file');
      return;
    }
    setUploading(true);
    try {
      const text = await file.text();
      if (activeList) {
        const result = await uploadCsvToList(activeList, text);
        toast.success(`${result.new_contacts} new, ${result.updated_contacts} updated — ${result.contact_count} total contacts`);
        setContactLists((prev) =>
          prev.map((l) => l.id === activeList ? { ...l, contact_count: result.contact_count, columns: result.columns } : l)
        );
      } else {
        const result = await uploadContactsCsv(text);
        toast.success(`${result.new_contacts} new, ${result.updated_contacts} updated — ${result.contact_count} total contacts`);
        getFilterOptions().then((opts) => {
          setPlanOptions(opts.plans);
          setSubscribedOptions(opts.subscribedValues);
        });
      }
      setSelectedIds(new Set());
      fetchContacts();
    } catch {
      toast.error('Failed to upload CSV');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  const handleDeleteList = (listId: string, listName: string) => {
    setDeleteTarget({ id: listId, name: listName });
  };

  const confirmDeleteList = async () => {
    if (!deleteTarget) return;
    try {
      await deleteContactList(deleteTarget.id);
      setContactLists((prev) => prev.filter((l) => l.id !== deleteTarget.id));
      if (activeList === deleteTarget.id) setActiveList(null);
      toast.success(`Deleted "${deleteTarget.name}"`);
    } catch {
      toast.error('Failed to delete list');
    } finally {
      setDeleteTarget(null);
    }
  };

  const activeListName = activeList
    ? contactLists.find((l) => l.id === activeList)?.name || 'Contact List'
    : 'All Contacts';

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-2xl font-bold">{activeListName}</h2>
        <div className="flex gap-2">
          <button
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
            onClick={() => setShowNewListModal(true)}
          >
            + Add New List
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            onChange={handleCsvUpload}
            className="hidden"
          />
          <button
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm disabled:opacity-50"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? 'Uploading...' : 'Add Data'}
          </button>
        </div>
      </div>

      {/* List tabs */}
      <div className="flex items-center gap-1 mb-4 border-b border-gray-200 overflow-x-auto">
        <button
          onClick={() => setActiveList(null)}
          className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
            activeList === null
              ? 'border-indigo-600 text-indigo-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          All Contacts
        </button>
        {contactLists.map((list) => (
          <div key={list.id} className="flex items-center group">
            <button
              onClick={() => setActiveList(list.id)}
              className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeList === list.id
                  ? 'border-indigo-600 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {list.name}
              <span className="ml-1.5 text-xs text-gray-400">({list.contact_count})</span>
            </button>
            <button
              onClick={() => handleDeleteList(list.id, list.name)}
              className="text-gray-300 hover:text-red-500 text-xs px-1 opacity-0 group-hover:opacity-100 transition-opacity"
              title="Delete list"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {activeList ? (
        <>
          {/* Simple search bar for dynamic lists */}
          <div className="mb-4 flex items-center gap-3">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search contacts..."
              className="w-full max-w-md border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              className="px-4 py-2 border border-gray-300 rounded text-sm font-medium text-gray-700 hover:bg-gray-100 whitespace-nowrap"
              onClick={() => {
                const allIds = dynamicContacts.map((c) => c.id as number);
                const allSelected = allIds.length > 0 && allIds.every((id) => selectedIds.has(id));
                setSelectedIds(allSelected ? new Set() : new Set(allIds));
              }}
            >
              {dynamicContacts.length > 0 && dynamicContacts.every((c) => selectedIds.has(c.id as number))
                ? 'Deselect All'
                : 'Select All'}
            </button>
            {selectedIds.size > 0 && (
              <button
                className="px-4 py-2 border border-red-300 rounded text-sm font-medium text-red-600 hover:bg-red-50 whitespace-nowrap"
                onClick={() => setSelectedIds(new Set())}
              >
                Clear Selection
              </button>
            )}
          </div>
          <DynamicContactTable
            contacts={dynamicContacts}
            columns={dynamicColumns}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
          />
        </>
      ) : (
        <>
          <MetricCards contacts={contacts} />
          <FilterBar
            search={search}
            subscribed={subscribed}
            plan={plan}
            planOptions={planOptions}
            subscribedOptions={subscribedOptions}
            onSearchChange={setSearch}
            onSubscribedChange={setSubscribed}
            onPlanChange={setPlan}
          />
          <div className="mb-3 flex items-center gap-3">
            <button
              className="px-4 py-2 border border-gray-300 rounded text-sm font-medium text-gray-700 hover:bg-gray-100"
              onClick={() => {
                const allIds = contacts.map((c) => c.id);
                const allSelected = allIds.length > 0 && allIds.every((id) => selectedIds.has(id));
                setSelectedIds(allSelected ? new Set() : new Set(allIds));
              }}
            >
              {contacts.length > 0 && contacts.every((c) => selectedIds.has(c.id))
                ? 'Deselect All'
                : 'Select All'}
            </button>
            {selectedIds.size > 0 && (
              <button
                className="px-4 py-2 border border-red-300 rounded text-sm font-medium text-red-600 hover:bg-red-50"
                onClick={() => setSelectedIds(new Set())}
              >
                Clear Selection
              </button>
            )}
          </div>
          <ContactTable
            contacts={contacts}
            selectedIds={selectedIds}
            onSelectionChange={setSelectedIds}
          />
        </>
      )}

      {selectedIds.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-indigo-600 text-white px-6 py-3 rounded-full shadow-lg flex items-center gap-4">
          <span className="text-sm font-medium">{selectedIds.size} selected</span>
          <button
            className="px-4 py-1.5 bg-white text-indigo-600 rounded-full text-sm font-medium hover:bg-indigo-50"
            onClick={handleCompose}
          >
            Compose Email
          </button>
        </div>
      )}

      <NewListModal
        open={showNewListModal}
        onClose={() => setShowNewListModal(false)}
        onCreated={(list) => {
          setContactLists((prev) => [...prev, list]);
          setActiveList(list.id);
        }}
      />

      <DeleteListModal
        open={!!deleteTarget}
        listName={deleteTarget?.name || ''}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDeleteList}
      />
    </div>
  );
}
