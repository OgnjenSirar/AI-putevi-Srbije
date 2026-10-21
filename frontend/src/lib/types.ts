export type Unit = { id: number; code: string; name: string }

export type CaseRow = {
  id: number
  number: string
  subject: string
  status: string
  priority: string
  category: string
  category_label: string
  org_unit: Unit | null
  customer: { id: number; name: string } | null
  assigned_to: { id: number; name: string } | null
  due_at: string | null
  created_at: string
  sla: string
  channel: string
  needs_billing_check: boolean
  billing_status?: string
  ai_status: string
  language: string
  script: string
  routing_confirmed: boolean
  snippet: string
}

export type EmailMsg = {
  id: number
  direction: 'in' | 'out'
  from_addr: string
  from_name: string
  to_addr: string
  subject: string
  body: string
  body_clean: string
  received_at: string
  attachments: { name: string; type: string; size: number; text?: string }[]
  message_id: string
  in_reply_to: string
  folder: string
  filter_reason: string
  language: string
  script: string
  headers: Record<string, string>
}

export type Warning = { nivo: string; tip: string; poruka: string }

export type Suggestion = {
  id: number
  created_at: string
  model: string
  mode: string
  prompt_version: string
  kb_version: string
  category: string
  suggested_unit: Unit | null
  suggested_priority: string
  reasoning: string
  confidence: number
  rule_overrides: { pravilo: string; poruka: string }[]
  entities: Record<string, string[] | string>
  billing_check: { potrebna?: boolean; tipovi?: string[]; sta_proveriti?: string }
  draft: string
  operator_note: string
  sources: { code: string; title: string; score: number; metode: string[]; koriscen: boolean }[]
  warnings: Warning[]
  finalized_at: string | null
  edit_class: string
  edit_ratio: number | null
  accepted_unit: boolean | null
  accepted_priority: boolean | null
  trace_id: string
}

export type CaseEvent = { id: number; at: string; actor: string; type: string; text: string; data: Record<string, unknown> }

export type Vehicle = { id: number; plate: string; category: string; tag_number: string; account_balance: number }

export type Customer = {
  id: number
  full_name: string
  customer_type: string
  company: string
  pib: string
  email: string
  phone: string
  city: string
  address: string
  source: string
  created_at: string
  merged_into_id: number | null
  note: string
  vehicles: Vehicle[]
  case_count?: number
  possible_duplicate?: boolean
}

export type PhoneContact = {
  id: number
  customer_id: number | null
  case_id: number | null
  direction: string
  phone: string
  staff: string
  started_at: string
  duration_sec: number
  topic: string
  note: string
}

export type CaseDetail = CaseRow & {
  billing_check: { potrebna?: boolean; tipovi?: string[]; sta_proveriti?: string; status?: string; rezultat?: string; proverio?: string }
  first_response_at: string | null
  closed_at: string | null
  customer_full: Customer | null
  emails: EmailMsg[]
  events: CaseEvent[]
  suggestion: Suggestion | null
  suggestion_count: number
  phone_contacts: PhoneContact[]
  other_cases: { id: number; number: string; subject: string; status: string; created_at: string; category_label: string }[]
}

export type Codebooks = Record<string, { id: number; code: string; label: string; data: Record<string, unknown>; active: boolean }[]>
