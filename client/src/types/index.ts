export interface Contact {
  id: number;
  username: string;
  email: string | null;
  online: string;
  first_name: string | null;
  last_name: string | null;
  mobile: string | null;
  subscribed: 'Yes' | 'No';
  plan: 'Free Trial' | 'Plus';
  pages_left: number;
  last_login: string | null;
  draft_used: number;
  research_used: number;
  contract_review: number;
  query_count: number;
  judgment_details: number;
  cart_item: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface Template {
  id: string;
  name: string;
  subject: string;
  body_html: string;
  body_text: string | null;
  preview_text: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface Email {
  id: string;
  template_id: string | null;
  subject: string;
  body_html: string;
  sender_email: string;
  status: string;
  total_recipients: number;
  total_opens: number;
  total_clicks: number;
  sent_at: string | null;
  created_at: string | null;
  scheduled_at: string | null;
  contact_ids: number[] | null;
}

export interface RecipientTracking {
  trackingId: string;
  contactId: number;
  emailId: string;
  email: string;
  name: string;
  opened_at: string | null;
  open_count: number;
  clicked_at: string | null;
  click_count: number;
}

export interface EmailDetail {
  email: Email;
  recipients: RecipientTracking[];
}

export interface ContactsResponse {
  data: Contact[];
  total: number;
  page: number;
  limit: number;
}

// Dynamic contact from CSV - any columns
export type DynamicContact = { id: number; [key: string]: string | number | null };

export interface DynamicContactsResponse {
  data: DynamicContact[];
  total: number;
  page: number;
  limit: number;
  columns: string[];
}

export interface FilterOptions {
  plans: string[];
  subscribedValues: string[];
}

export interface ContactList {
  id: string;
  name: string;
  contact_count: number;
  created_at: string | null;
  columns?: string[];
}