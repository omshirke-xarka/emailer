import axios from 'axios';
import type { Contact, ContactsResponse, DynamicContactsResponse, FilterOptions, Template, Email, EmailDetail, ContactList, EmailProvider } from '../types';

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api' });

// Contacts
export const getContacts = (params?: Record<string, string>) =>
  api.get<ContactsResponse>('/contacts', { params }).then((r) => r.data);

export const createContact = (data: Partial<Contact>) =>
  api.post<Contact>('/contacts', data).then((r) => r.data);

export const updateContact = (id: number, data: Partial<Contact>) =>
  api.put<Contact>(`/contacts/${id}`, data).then((r) => r.data);

export const deleteContact = (id: number) =>
  api.delete(`/contacts/${id}`);

export const importContacts = (contacts: Partial<Contact>[]) =>
  api.post('/contacts/import', { contacts }).then((r) => r.data);

export const getFilterOptions = () =>
  api.get<FilterOptions>('/contacts/filters').then((r) => r.data);

export const uploadContactsCsv = (csv: string) =>
  api.post<{ contact_count: number; new_contacts: number; updated_contacts: number }>('/contacts/upload-csv', { csv }).then((r) => r.data);

// Contact Lists
export const getContactLists = () =>
  api.get<ContactList[]>('/contacts/lists').then((r) => r.data);

export const createContactList = (name: string, csv: string) =>
  api.post<ContactList>('/contacts/lists', { name, csv }).then((r) => r.data);

export const getContactsForList = (listId: string, params?: Record<string, string>) =>
  api.get<DynamicContactsResponse>(`/contacts/lists/${listId}`, { params }).then((r) => r.data);

export const uploadCsvToList = (listId: string, csv: string) =>
  api.post<{ contact_count: number; new_contacts: number; updated_contacts: number; columns: string[] }>(`/contacts/lists/${listId}/upload-csv`, { csv }).then((r) => r.data);

export const deleteContactList = (listId: string) =>
  api.delete(`/contacts/lists/${listId}`);

// Templates
export const getTemplates = () =>
  api.get<{ data: Template[] }>('/templates').then((r) => r.data.data);

export const getTemplate = (id: string) =>
  api.get<Template>(`/templates/${id}`).then((r) => r.data);

export const createTemplate = (data: Partial<Template>) =>
  api.post<Template>('/templates', data).then((r) => r.data);

export const updateTemplate = (id: string, data: Partial<Template>) =>
  api.put<Template>(`/templates/${id}`, data).then((r) => r.data);

export const deleteTemplate = (id: string) =>
  api.delete(`/templates/${id}`);

// Emails
export const sendEmail = (data: {
  contactIds: number[];
  subject: string;
  bodyHtml: string;
  templateId?: string;
  previewText?: string;
  listId?: string;
}) => api.post<{ sent: number; failed: number; email_id: string }>('/emails/send', {
  contact_ids: data.contactIds,
  subject: data.subject,
  body_html: data.bodyHtml,
  template_id: data.templateId,
  preview_text: data.previewText,
  list_id: data.listId,
}).then((r) => r.data);

export const previewEmail = (bodyHtml: string, contactId?: number, listId?: string) =>
  api.post<{ html: string }>('/emails/preview', { body_html: bodyHtml, contact_id: contactId, list_id: listId }).then((r) => r.data);

export const getEmails = () =>
  api.get<{ data: Email[] }>('/emails').then((r) => r.data.data);

export const getEmailDetail = (id: string) =>
  api.get<EmailDetail>(`/emails/${id}`).then((r) => r.data);

export const retryEmail = (id: string) =>
  api.post<{ sent: number; failed: number; email_id: string }>(`/emails/${id}/retry`).then((r) => r.data);

export const scheduleEmail = (data: {
  contactIds: number[];
  subject: string;
  bodyHtml: string;
  templateId?: string;
  previewText?: string;
  scheduledAt: string;
  listId?: string;
}) => api.post<{ emailId: string; scheduledAt: string }>('/emails/schedule', data).then((r) => r.data);

export const getScheduledEmails = () =>
  api.get<{ data: Email[] }>('/emails/scheduled').then((r) => r.data.data);

export const cancelScheduledEmail = (id: string) =>
  api.post<{ success: boolean }>(`/emails/${id}/cancel`).then((r) => r.data);

export const getEmailProvider = () =>
  api.get<{ provider: EmailProvider }>('/emails/provider').then((r) => r.data);

export const updateEmailProvider = (provider: EmailProvider) =>
  api.put<{ provider: EmailProvider }>('/emails/provider', { provider }).then((r) => r.data);

// Uploads
export const uploadImage = (file: File): Promise<{ url: string }> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const base64 = (reader.result as string).split(',')[1];
      api.post<{ url: string }>('/uploads/image', {
        filename: file.name,
        contentType: file.type,
        data: base64,
      }).then((r) => resolve(r.data)).catch(reject);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};
