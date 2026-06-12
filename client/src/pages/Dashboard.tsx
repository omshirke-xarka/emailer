import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import DynamicContactTable from '../components/DynamicContactTable';
import {

  getContactLists,
  createContactList,
  getContactsForList,
  uploadContactsCsv,
  uploadCsvToList,
  deleteContactList,
  createContact,
  addContactToList,
} from '../api/client';
import type { ContactList, DynamicContact } from '../types';
import { fileToCsv, isSpreadsheetFile, SPREADSHEET_ACCEPT } from '../utils/fileToCsv';

const ALL_CONTACT_FIELDS = [
  { key: 'username', label: 'Username', required: true },
  { key: 'email', label: 'Email', required: true },
  { key: 'first_name', label: 'First name', required: false },
  { key: 'last_name', label: 'Last name', required: false },
  { key: 'mobile', label: 'Mobile', required: false },
];

function AddContactModal({
  open,
  onClose,
  listId,
  columns,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  listId: string;
  columns: string[];
  onCreated: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  if (!open) return null;

  const isAllContacts = listId === 'all';
  const listColumns = columns.filter((c) => c !== 'id');
  const emailColumn = listColumns.find((c) => c.toLowerCase().includes('email')) || listColumns[0];

  const setValue = (key: string, value: string) =>
    setValues((prev) => ({ ...prev, [key]: value }));

  const resetAndClose = () => {
    setValues({});
    onClose();
  };

  const handleSave = async () => {
    if (isAllContacts) {
      if (!values.username?.trim() || !values.email?.trim()) {
        toast.error('Username and Email are required');
        return;
      }
    } else if (!values[emailColumn]?.trim()) {
      toast.error(`${emailColumn} is required`);
      return;
    }

    setSaving(true);
    try {
      if (isAllContacts) {
        await createContact({
          username: values.username.trim(),
          email: values.email.trim(),
          first_name: values.first_name?.trim() || null,
          last_name: values.last_name?.trim() || null,
          mobile: values.mobile?.trim() || null,
        });
      } else {
        await addContactToList(listId, values);
      }
      toast.success('Contact added');
      setValues({});
      onCreated();
      onClose();
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Failed to add contact');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-lg font-semibold mb-4">Add Contact</h3>

        {isAllContacts ? (
          ALL_CONTACT_FIELDS.map((field, i) => (
            <div key={field.key} className="mb-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label}
                {field.required && <span className="text-red-500"> *</span>}
              </label>
              <input
                type={field.key === 'email' ? 'email' : 'text'}
                value={values[field.key] || ''}
                onChange={(e) => setValue(field.key, e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                autoFocus={i === 0}
              />
            </div>
          ))
        ) : (
          listColumns.map((col, i) => (
            <div key={col} className="mb-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {col}
                {col === emailColumn && <span className="text-red-500"> *</span>}
              </label>
              <input
                type="text"
                value={values[col] || ''}
                onChange={(e) => setValue(col, e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                autoFocus={i === 0}
              />
            </div>
          ))
        )}

        <div className="flex justify-end gap-3 mt-4">
          <button
            onClick={resetAndClose}
            className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800"
            disabled={saving}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 text-sm disabled:opacity-50"
          >
            {saving ? 'Adding...' : 'Add Contact'}
          </button>
        </div>
      </div>
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
      toast.error('Please select a CSV or Excel file');
      return;
    }
    setCreating(true);
    try {
      const text = await fileToCsv(file);
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

        <label className="block text-sm font-medium text-gray-700 mb-1">CSV or Excel File</label>
        <input
          ref={fileRef}
          type="file"
          accept={SPREADSHEET_ACCEPT}
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="w-full border-2 border-dashed border-gray-300 rounded px-3 py-4 text-sm text-gray-500 hover:border-indigo-400 hover:text-indigo-600 transition mb-4"
        >
          {file ? file.name : 'Click to select a CSV or Excel file'}
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
  const [dynamicContacts, setDynamicContacts] = useState<DynamicContact[]>([]);
  const [dynamicColumns, setDynamicColumns] = useState<string[]>([]);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Contact lists
  const [contactLists, setContactLists] = useState<ContactList[]>([]);
  const [activeList, setActiveList] = useState<string>('all');
  const [allContactsTotal, setAllContactsTotal] = useState(0);
  const [showNewListModal, setShowNewListModal] = useState(false);
  const [showAddContactModal, setShowAddContactModal] = useState(false);

  // Debounce search input by 300ms
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(timer);
  }, [search]);

  // Load contact lists
  useEffect(() => {
    getContactLists().then(setContactLists).catch(() => {});
  }, []);

  const fetchContacts = useCallback(async () => {
    try {
      const params: Record<string, string> = {};
      if (debouncedSearch) params.search = debouncedSearch;
      params.limit = '0';

      const res = await getContactsForList(activeList, params);
      setDynamicContacts(res.data);
      setDynamicColumns(res.columns || []);
      if (activeList === 'all') {
        setAllContactsTotal(res.total);
      }
    } catch {
      toast.error('Failed to load contacts');
    }
  }, [debouncedSearch, activeList]);

  // Clear selection and search when switching lists
  useEffect(() => {
    setSelectedIds(new Set());
    setSearch('');
    setDebouncedSearch('');
  }, [activeList]);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  const handleCompose = () => {
    const ids = Array.from(selectedIds);
    navigate('/compose', {
      state: {
        contactIds: ids,
        listId: activeList === 'all' ? null : activeList,
      },
    });
  };

  const handleCsvUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!isSpreadsheetFile(file.name)) {
      toast.error('Please select a CSV or Excel file');
      return;
    }
    setUploading(true);
    try {
      const text = await fileToCsv(file);
      const result = activeList === 'all'
        ? await uploadContactsCsv(text)
        : await uploadCsvToList(activeList, text);
      toast.success(`${result.new_contacts} new, ${result.updated_contacts} updated — ${result.contact_count} total contacts`);
      if (activeList === 'all') {
        setAllContactsTotal(result.contact_count);
      } else {
        setContactLists((prev) =>
          prev.map((l) => l.id === activeList ? { ...l, contact_count: result.contact_count, columns: result.columns } : l)
        );
      }
      setSelectedIds(new Set());
      fetchContacts();
    } catch {
      toast.error('Failed to upload file');
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
      if (activeList === deleteTarget.id) setActiveList('all');
      toast.success(`Deleted "${deleteTarget.name}"`);
    } catch {
      toast.error('Failed to delete list');
    } finally {
      setDeleteTarget(null);
    }
  };

  const visibleContactLists: ContactList[] = [
    {
      id: 'all',
      name: 'All Contacts',
      contact_count: allContactsTotal,
      created_at: null,
      columns: dynamicColumns,
    },
    ...contactLists,
  ];

  const activeListName = activeList === 'all'
    ? 'All Contacts'
    : contactLists.find((l) => l.id === activeList)?.name || 'Contact List';

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
          <button
            className="px-4 py-2 bg-white border border-indigo-600 text-indigo-600 rounded hover:bg-indigo-50 text-sm"
            onClick={() => setShowAddContactModal(true)}
          >
            + Add Contact
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept={SPREADSHEET_ACCEPT}
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
        {visibleContactLists.map((list) => (
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
            {list.id !== 'all' && (
              <button
                onClick={() => handleDeleteList(list.id, list.name)}
                className="text-gray-300 hover:text-red-500 text-xs px-1 opacity-0 group-hover:opacity-100 transition-opacity"
                title="Delete list"
              >
                ✕
              </button>
            )}
          </div>
        ))}
      </div>

      <>
        {/* Search and selection controls */}
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

      <AddContactModal
        open={showAddContactModal}
        onClose={() => setShowAddContactModal(false)}
        listId={activeList}
        columns={dynamicColumns}
        onCreated={() => {
          if (activeList !== 'all') {
            setContactLists((prev) =>
              prev.map((l) => l.id === activeList ? { ...l, contact_count: l.contact_count + 1 } : l)
            );
          }
          fetchContacts();
        }}
      />

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
