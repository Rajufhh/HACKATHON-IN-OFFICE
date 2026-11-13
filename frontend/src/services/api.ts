import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1",
  timeout: 20000,
});

export interface Learner {
  id: number;
  learner_code: string;
  name: string;
  email: string;
  department: string;
  status: string;
}

export interface Assessment {
  id: number;
  assessment_code: string;
  title: string;
  assessment_type: string;
  status: string;
}

export interface Reviewer {
  id: number;
  reviewer_code: string;
  full_name: string;
  email: string;
  department: string;
  status: string;
}

export interface Submission {
  id: number;
  submission_code: string;
  learner_id: number;
  assessment_id: number;
  submitted_at: string;
  file_reference: string | null;
  content_hash: string | null;
  version_number: number;
  status: string;
}

export interface Flag {
  id: number;
  flag_code: string;
  submission_id: number;
  report_id: number;
  integrity_rule_id: number;
  flag_type: string;
  status: string;
  reason: string | null;
  created_at: string;
}

export interface CaseRecord {
  id: number;
  case_code: string;
  learner_id: number;
  status: string;
  priority: string;
  title: string;
  description: string | null;
  opened_at: string;
  closed_at: string | null;
}

export interface CaseEvent {
  id: number;
  case_id: number;
  event_type: string;
  description: string;
  actor_id: number | null;
  actor_role: string | null;
  created_at: string;
}

export interface CaseAssignment {
  id: number;
  case_id: number;
  reviewer_id: number;
  conflict_status: string;
  assigned_at: string;
  unassigned_at: string | null;
  status: string;
}

export interface CaseDetail extends CaseRecord {
  events: CaseEvent[];
  assignments: CaseAssignment[];
}

export interface Evidence {
  id: number;
  evidence_code: string;
  case_id: number;
  evidence_type: string;
  title: string;
  description: string | null;
  source_reference: string | null;
  added_at: string;
}

export interface Decision {
  id: number;
  decision_code: string;
  case_id: number;
  reviewer_id: number;
  outcome: string;
  rationale: string;
  decided_at: string;
}

export interface SimilarityReport {
  id: number;
  report_code: string;
  submission_id: number;
  overall_score: number;
  quotation_percentage: number;
  template_percentage: number;
  internet_percentage: number;
  analyzed_at: string;
  status: string;
}

export interface AnalysisResult {
  report: SimilarityReport;
  rule_action: string;
  flag_created: boolean;
  flag: Flag | null;
  due_process_notice: string;
}

export interface GeneratedDatasetFile {
  filename: string;
  category: "input_data" | "evaluation_labels" | "database_seed" | "documentation";
  size_bytes: number;
}

export interface GeneratedDatasetInfo {
  status: string;
  metrics: Record<string, unknown>;
  row_counts: Record<string, number>;
  files: GeneratedDatasetFile[];
}

export interface Appeal {
  id: number;
  appeal_code: string;
  decision_id: number;
  learner_id: number;
  assigned_reviewer_id: number | null;
  grounds: string;
  status: string;
  outcome: string | null;
  outcome_rationale: string | null;
  submitted_at: string;
  assigned_at: string | null;
  resolved_at: string | null;
}

export interface AppealEvent {
  id: number;
  appeal_id: number;
  event_type: string;
  description: string;
  actor_id: number | null;
  actor_role: string | null;
  created_at: string;
}

export interface AppealDetail extends Appeal {
  events: AppealEvent[];
  evidence_snapshots: Array<{
    id: number;
    evidence_id: number;
    evidence_code_snapshot: string;
    evidence_title_snapshot: string;
    evidence_type_snapshot: string;
    added_by: number | null;
    added_at: string;
  }>;
}

export interface DecisionDetail extends Decision {
  evidence_snapshot: Array<{
    id: number;
    evidence_id: number;
    evidence_code_snapshot: string;
    evidence_title_snapshot: string;
    evidence_type_snapshot: string;
  }>;
}

export const apiClient = {
  listLearners: () => api.get<Learner[]>("/learners/").then((response) => response.data),
  listAssessments: () => api.get<Assessment[]>("/assessments/").then((response) => response.data),
  listReviewers: () => api.get<Reviewer[]>("/reviewers/").then((response) => response.data),
  listSubmissions: () => api.get<Submission[]>("/submissions/").then((response) => response.data),
  listFlags: () => api.get<Flag[]>("/similarity/flags").then((response) => response.data),
  listCases: () => api.get<CaseRecord[]>("/cases/").then((response) => response.data),
  listAppeals: () => api.get<Appeal[]>("/appeals/").then((response) => response.data),
  getGeneratedDatasetInfo: () =>
    api.get<GeneratedDatasetInfo>("/datasets/generated").then((response) => response.data),
  downloadGeneratedDatasetFile: (filename: string) =>
    api.get<Blob>(`/datasets/generated/files/${encodeURIComponent(filename)}`, {
      responseType: "blob",
    }).then((response) => response.data),

  createSubmission: (payload: {
    submission_code: string;
    learner_id: number;
    assessment_id: number;
    file_reference?: string;
  }) => api.post<Submission>("/submissions/", payload).then((response) => response.data),
  deleteSubmission: (submissionId: number) =>
    api.delete<void>(`/submissions/${submissionId}`).then(() => undefined),
  analyzeSubmission: (submissionId: number) =>
    api.post<AnalysisResult>(`/similarity/analyze/${submissionId}`).then((response) => response.data),

  createCase: (payload: {
    case_code: string;
    flag_id: number;
    title: string;
    description?: string;
  }) => api.post<CaseRecord>("/cases/", payload).then((response) => response.data),
  getCase: (caseId: number, signal?: AbortSignal) =>
    api.get<CaseDetail>(`/cases/${caseId}`, { signal }).then((response) => response.data),
  assignCase: (caseId: number, reviewerId: number) =>
    api.post<CaseRecord>(`/cases/${caseId}/assign`, { reviewer_id: reviewerId }).then((response) => response.data),
  updateCaseStatus: (caseId: number, status: string, reason: string) =>
    api.patch<CaseRecord>(`/cases/${caseId}/status`, { status, reason }).then((response) => response.data),
  listEvidence: (caseId: number, signal?: AbortSignal) =>
    api.get<Evidence[]>(`/evidence/case/${caseId}`, { signal }).then((response) => response.data),
  createEvidence: (payload: {
    case_id: number;
    evidence_type: string;
    title: string;
    description?: string;
    source_reference?: string;
  }) => api.post<Evidence>("/evidence/", payload).then((response) => response.data),
  listCaseDecisions: (caseId: number, signal?: AbortSignal) =>
    api.get<Decision[]>(`/decisions/case/${caseId}`, { signal }).then((response) => response.data),
  createDecision: (payload: {
    case_id: number;
    reviewer_id: number;
    outcome: string;
    rationale: string;
    evidence_ids: number[];
  }) => api.post<Decision>("/decisions/", payload).then((response) => response.data),

  createAppeal: (payload: {
    decision_id: number;
    learner_id: number;
    grounds: string;
  }) => api.post<Appeal>("/appeals/", payload).then((response) => response.data),
  getAppeal: (appealId: number, signal?: AbortSignal) =>
    api.get<AppealDetail>(`/appeals/${appealId}`, { signal }).then((response) => response.data),
  getDecision: (decisionId: number, signal?: AbortSignal) =>
    api.get<DecisionDetail>(`/decisions/${decisionId}`, { signal }).then((response) => response.data),
  assignAppeal: (appealId: number, reviewerId: number) =>
    api.post<Appeal>(`/appeals/${appealId}/assign`, { reviewer_id: reviewerId }).then((response) => response.data),
  addAppealEvidence: (appealId: number, evidenceId: number) =>
    api.post(`/appeals/${appealId}/evidence`, { evidence_id: evidenceId }).then((response) => response.data),
  resolveAppeal: (
    appealId: number,
    reviewerId: number,
    outcome: string,
    rationale: string,
  ) => api.post<Appeal>(`/appeals/${appealId}/resolve`, {
    reviewer_id: reviewerId,
    outcome,
    rationale,
  }).then((response) => response.data),
};

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail: unknown = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" && item !== null && "msg" in item
            ? String(item.msg)
            : "",
        )
        .filter(Boolean)
        .join("; ");
    }
    return error.message || "The backend request failed.";
  }
  return error instanceof Error ? error.message : "The backend request failed.";
}
