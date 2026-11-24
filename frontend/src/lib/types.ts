/** Shapes returned by the Ficka API (see backend `app/api/*.py`). */

export type Direction = 'income' | 'expense';
export type EntryStatus = 'proposed' | 'confirmed';
export type EntrySource = 'manual' | 'recurring' | 'document' | 'bank';
export type PaymentStatus = 'unpaid' | 'partial' | 'paid' | 'overdue';
export type CounterpartyRole = 'customer' | 'supplier' | 'both';

export interface Ref {
  id: number;
  name: string;
}

export interface VatRate {
  rate_bp: number;
  label: string;
}

export interface CompanySettings {
  amounts_include_vat_default: boolean;
  locale: string;
  country_code: string;
  currency: string;
}

export interface Category {
  id: number;
  direction: Direction;
  name: string;
  default_vat_rate_bp: number | null;
  position: number;
  is_seeded: boolean;
  usage: { entries: number; templates: number; counterparties: number };
}

/** A counterparty as the entry form's combobox knows it. */
export interface CounterpartyChoice {
  id: number;
  name: string;
  default_category_id: number | null;
  default_vat_rate_bp: number | null;
}

export interface CounterpartyListItem {
  id: number;
  name: string;
  role: CounterpartyRole;
  vat_number: string | null;
  default_category_id: number | null;
  default_vat_rate_bp: number | null;
  entries_count: number;
  open_balance_cents: number;
}

/** The counterparty form's fields, as text (what the inputs hold). */
export interface CounterpartyFormValues {
  name: string;
  role: CounterpartyRole;
  vat_number: string;
  ibans: string[];
  default_category_id: string;
  default_vat_rate_bp: string;
  notes: string;
}

export interface Counterparty {
  id: number;
  name: string;
  role: CounterpartyRole;
  vat_number: string | null;
  ibans: string[];
  default_category_id: number | null;
  default_vat_rate_bp: number | null;
  notes: string | null;
  stats: {
    entries_count: number;
    income_total_cents: number;
    expense_total_cents: number;
    open_balance_cents: number;
  };
}

export interface EntryListItem {
  id: number;
  direction: Direction;
  status: EntryStatus;
  source: EntrySource;
  invoice_date: string;
  due_date: string | null;
  counterparty: Ref | null;
  category: Ref | null;
  description: string | null;
  invoice_number: string | null;
  total_net_cents: number;
  total_vat_cents: number;
  total_gross_cents: number;
  paid_cents: number;
  payment_status: PaymentStatus;
}

export interface EntryList {
  items: EntryListItem[];
  total: number;
  summary: {
    income_gross_cents: number;
    expense_gross_cents: number;
    income_net_cents: number;
    expense_net_cents: number;
  };
}

export interface EntryLine {
  id: number;
  position: number;
  description: string | null;
  net_cents: number;
  vat_rate_bp: number | null;
  vat_cents: number;
  gross_cents: number;
  vat_manual: boolean;
}

export interface Payment {
  id: number;
  paid_on: string;
  amount_cents: number;
  source: 'manual' | 'assumed' | 'bank';
  note: string | null;
}

export interface EntryWarning {
  code: string;
  message: string;
}

export interface Entry extends EntryListItem {
  structured_reference: string | null;
  amounts_include_vat: boolean;
  document_location: string | null;
  confirmed_at: string | null;
  created_at: string;
  updated_at: string;
  remaining_cents: number;
  lines: EntryLine[];
  payments: Payment[];
  warnings: EntryWarning[];
}

/** What the entry form sends to its action, as one JSON `payload` field. */
export interface EntryPayload {
  direction: Direction;
  invoice_date: string;
  due_date: string | null;
  counterparty_id: number | null;
  category_id: number | null;
  description: string | null;
  invoice_number: string | null;
  structured_reference: string | null;
  amounts_include_vat: boolean;
  document_location: string | null;
  lines: {
    description: string | null;
    net_cents?: number;
    gross_cents?: number;
    vat_rate_bp: number | null;
    vat_cents?: number;
    vat_manual: boolean;
  }[];
  paid_on?: string | null;
}

export const PAYMENT_STATUS_LABELS: Record<PaymentStatus, string> = {
  unpaid: 'Unpaid',
  partial: 'Partly paid',
  paid: 'Paid',
  overdue: 'Overdue'
};

export const ROLE_LABELS: Record<CounterpartyRole, string> = {
  customer: 'Customer',
  supplier: 'Supplier',
  both: 'Customer and supplier'
};
