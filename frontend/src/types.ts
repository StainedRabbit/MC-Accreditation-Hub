export type Assignment = {
  role: string;
  cycle_id: number;
  area_id: number | null;
};
export type User = {
  id: number;
  name: string;
  username: string;
  is_staff: boolean;
  assignments: Assignment[];
};
export type Cycle = {
  id: number;
  title: string;
  program: string;
  status: string;
  is_demo: boolean;
};
export type Summary = {
  total: number;
  complete: number;
  ready_for_completion_review: number;
  pending: number;
  for_compliance: number;
  missing: number;
  excluded: number;
  percentage: number | null;
  formula: string;
};
export type Area = Summary & {
  id: number;
  cycle: number;
  title: string;
  code: string;
  icon: string;
  can_manage: boolean;
  can_upload: boolean;
};
export type Decision = {
  outcome: string;
  comment: string;
  reviewer: string;
  created_at: string;
};
export type Submission = {
  id: number;
  mapping: number;
  version: number;
  version_number: number;
  document_title: string;
  document: string;
  item_label: string;
  requirement: number;
  requirement_title: string;
  submitted_at: string;
  submitted_by: string;
  status: string;
  current: boolean;
  can_review: boolean;
  decision: Decision | null;
};
export type Mapping = {
  id: number;
  document: string;
  document_title: string;
  item: number;
  submissions: Submission[];
};
export type Item = {
  id: number;
  label: string;
  criteria: string;
  mandatory: boolean;
  status: string;
  mappings: Mapping[];
};
export type Requirement = {
  id: number;
  code: string;
  title: string;
  description: string;
  area: number;
  area_title: string;
  cycle: number;
  icon: string;
  responsible: string;
  deadline: string | null;
  active: boolean;
  applicable: boolean;
  exclusion_reason: string;
  status: string;
  approved_items: number;
  required_items: number;
  can_manage: boolean;
  can_upload: boolean;
  can_complete?: boolean;
  can_reopen?: boolean;
  certifications?: Certification[];
  items?: Item[];
};
export type Certification = {
  id: number;
  outcome: "complete" | "reopened";
  coordinator: string;
  rationale: string;
  created_at: string;
};
export type Version = {
  id: number;
  number: number;
  original_name: string;
  content_type: string;
  size: number;
  checksum: string;
  uploaded_by: string;
  uploaded_at: string;
  valid_until: string | null;
  download_url: string;
};
export type Document = {
  id: string;
  title: string;
  category: string;
  area: number;
  area_title: string;
  cycle: number;
  custodian: string;
  versions: Version[];
  can_upload: boolean;
  mappings: Mapping[];
};
export type Audit = {
  id: number;
  actor: string;
  action: string;
  record: string;
  created_at: string;
};
export type SearchResults = {
  requirements: Array<{ id: number; code: string; title: string; area: string; status: string }>;
  documents: Array<{ id: string; title: string; category: string; area: string }>;
};
export type ComplianceReport = Summary & {
  calculated_at: string;
  scope: string;
  rows: Array<{
    id: number;
    code: string;
    title: string;
    area: string;
    responsible: string;
    deadline: string | null;
    status: string;
    approved_items: number;
    required_items: number;
  }>;
};
