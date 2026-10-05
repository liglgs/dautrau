export type Role = "reviewer" | "clinician" | "responder" | "admin";
export type User = { id: string; name: string; role: Role };
export type Lifecycle = "draft" | "reviewing" | "approved" | "changes_pending";
export type RunStatus =
  | "queued"
  | "running"
  | "waiting_event"
  | "completed"
  | "failed"
  | "budget_exhausted";
export type WorkStatus =
  | "new"
  | "investigating"
  | "waiting_response"
  | "ready_for_review"
  | "closed"
  | "handed_off";
export type EvidenceStatus =
  | "unknown"
  | "documented_explanation"
  | "confirmed_information_resolved"
  | "confirmed_no_difference"
  | "confirmed_intentional"
  | "confirmed_unintentional"
  | "inconclusive";
export type SourceKind =
  | "prior_prescription"
  | "medication_history"
  | "admission_order"
  | "clinical_note"
  | "verification_response";
export type Source = {
  source_id: string;
  version: number;
  kind: SourceKind;
  filename: string;
  author_role: string;
  event_time: string | null;
  recorded_at: string | null;
  available_at: string;
  text: string;
};
export type Evidence = {
  id: string;
  source_id: string;
  version: number;
  quote: string;
  context: string;
};
export type Assertion = {
  id: string;
  revision: number;
  name: string;
  product: string | null;
  dose: string | null;
  frequency: string | null;
  side: "history" | "order";
  assertion_type:
    | "prescribed"
    | "patient_reported_taking"
    | "ordered"
    | "documented_not_taking"
    | "uncertain";
  evidence_ids: string[];
};
export type Issue = {
  id: string;
  revision: number;
  title: string;
  type: "information_gap" | "presence_difference" | "regimen_difference";
  work_status: WorkStatus;
  evidence_status: EvidenceStatus;
  evidence_ids: string[];
  assertion_refs?: string[];
  confirmation?: {
    type: EvidenceStatus;
    reason: string;
    actor: string;
    evidence_ids: string[];
  };
  history: string[];
};
export type Task = {
  id: string;
  case_id: string;
  issue_id: string;
  revision: number;
  assignee: string;
  question: string;
  missing_fields: string[];
  evidence_ids: string[];
  status: "open" | "answered" | "cancelled" | "handed_off";
  response?: string;
  reason?: string;
};
export type Handoff = {
  id: string;
  case_id: string;
  issue_id: string;
  revision: number;
  recipient: string;
  reason: string;
  acknowledged: boolean;
};
export type Review = {
  id: string;
  case_id: string;
  revision: number;
  case_revision: number;
  status: "draft" | "approved" | "superseded";
  approved_by?: string;
  approved_at?: string;
  snapshot: {
    assertions: Assertion[];
    issues: Issue[];
    sources: Source[];
    evidence: Evidence[];
    audit: string[];
    reconciliation_at: string;
  };
};
export type Case = {
  id: string;
  patient_id: string;
  encounter_id: string;
  reconciliation_at: string;
  visible_at: string;
  lifecycle: Lifecycle;
  revision: number;
  assigned: string[];
  scenario: "matched" | "verification" | "late" | null;
  run: { id: string; status: RunStatus; error?: string | null } | null;
  sources: Source[];
  evidence: Evidence[];
  assertions: Assertion[];
  issues: Issue[];
  audit: string[];
  extraction_pending: boolean;
};
export type Store = {
  cases: Case[];
  tasks: Task[];
  handoffs: Handoff[];
  reviews: Review[];
  receipts: Record<string, { payload: string; response: unknown }>;
  chatMessages?: ChatMessage[];
  dispatches?: DispatchRecord[];
};
export type ChatCitation = {
  source_id: string;
  version: number;
  quote: string;
};
export type ChatMessage = {
  id: string;
  case_id: string;
  sender: "user" | "agent";
  text: string;
  timestamp: string;
  citations?: ChatCitation[];
  reasoning?: string[];
};
export type DispatchRecord = {
  id: string;
  case_id: string;
  patient_id: string;
  assigned_reviewer: string;
  assigned_clinician: string;
  priority: "normal" | "high" | "urgent";
  status: "unassigned" | "assigned" | "in_progress" | "escalated";
  notes?: string;
  updated_at: string;
};
export type DashboardMetrics = {
  total_cases: number;
  matched_count: number;
  gap_count: number;
  diff_count: number;
  approved_count: number;
  avg_time_mins: number;
  agent_status: "online" | "idle" | "error";
  agent_model: string;
  total_tokens: number;
  avg_latency_ms: number;
  calls_today: number;
  recent_audits: { id: string; time: string; actor: string; action: string; case_id?: string }[];
};
export type Manifest = {
  schema_version: string;
  case_id: string;
  patient_id: string;
  encounter_id: string;
  reconciliation_at: string;
  initial_visible_at: string;
  documents: Omit<Source, "text">[];
};
export const labels: Record<string, string> = {
  draft: "Chưa xử lý",
  reviewing: "Đang rà soát",
  approved: "Đã duyệt",
  changes_pending: "Cần rà lại",
  queued: "Đang xếp hàng",
  running: "Đang xử lý",
  waiting_event: "Chờ sự kiện",
  completed: "Hoàn tất lượt xử lý",
  failed: "Lỗi xử lý",
  budget_exhausted: "Hết giới hạn xử lý",
  new: "Mới",
  investigating: "Đang tìm bằng chứng",
  waiting_response: "Chờ phản hồi",
  ready_for_review: "Chờ rà soát",
  closed: "Đã đóng",
  handed_off: "Đã bàn giao",
  unknown: "Chưa xác định",
  documented_explanation: "Có lời giải thích",
  confirmed_information_resolved: "Đã làm rõ thông tin",
  confirmed_no_difference: "Không khác trong phạm vi so sánh",
  confirmed_intentional: "Khác biệt có chủ ý",
  confirmed_unintentional: "Khác biệt không chủ ý",
  inconclusive: "Chưa thể kết luận",
  prescribed: "Từng được kê",
  patient_reported_taking: "Khai đang dùng",
  ordered: "Có y lệnh",
  documented_not_taking: "Ghi nhận không dùng",
  uncertain: "Chưa rõ",
  open: "Đang mở",
  answered: "Đã trả lời",
  cancelled: "Đã hủy",
  superseded: "Bản cũ",
  prior_prescription: "Đơn thuốc cũ",
  medication_history: "Tiền sử dùng thuốc",
  admission_order: "Y lệnh nhập viện",
  clinical_note: "Ghi chú",
  verification_response: "Phản hồi xác minh",
  unassigned: "Chưa phân công",
  assigned: "Đã phân công",
  in_progress: "Đang xử lý",
  escalated: "Cần can thiệp gấp",
  normal: "Bình thường",
  high: "Ưu tiên cao",
  urgent: "Khẩn cấp",
  online: "Trực tuyến · Sẵn sàng",
  idle: "Chờ lệnh",
  error: "Gặp sự cố",
};
