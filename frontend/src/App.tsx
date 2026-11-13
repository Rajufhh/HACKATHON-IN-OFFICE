import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  AlertCircle,
  ArrowUpRight,
  Check,
  Database,
  FilePlus2,
  FolderKanban,
  Gavel,
  LoaderCircle,
  RefreshCw,
  Scale,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import {
  apiClient,
  getApiError,
  type Appeal,
  type AppealDetail,
  type Assessment,
  type CaseDetail,
  type CaseRecord,
  type Decision,
  type DecisionDetail,
  type Evidence,
  type Flag,
  type Learner,
  type Reviewer,
  type Submission,
  type AnalysisResult,
} from "./services/api";
import { DataLab } from "./components/DataLab";
import "./App.css";

type Section = "cases" | "appeals" | "submissions" | "data";

interface Workspace {
  learners: Learner[];
  assessments: Assessment[];
  reviewers: Reviewer[];
  submissions: Submission[];
  flags: Flag[];
  cases: CaseRecord[];
  appeals: Appeal[];
}

const emptyWorkspace: Workspace = {
  learners: [],
  assessments: [],
  reviewers: [],
  submissions: [],
  flags: [],
  cases: [],
  appeals: [],
};

const sectionLabels: Record<Section, string> = {
  cases: "Casework",
  appeals: "Appeals",
  submissions: "Submissions",
  data: "Dataset tools",
};

const nextCaseStatuses: Record<string, string[]> = {
  OPEN: ["ASSIGNED"],
  ASSIGNED: ["UNDER_REVIEW"],
  UNDER_REVIEW: ["DECISION_PENDING"],
  DECISION_PENDING: ["CLOSED"],
  CLOSED: [],
};
const decisionOutcomes = [
  "BREACH_ESTABLISHED",
  "NO_BREACH",
  "INSUFFICIENT_EVIDENCE",
  "REFERRED_FOR_FURTHER_REVIEW",
];
const appealOutcomes = ["UPHELD", "OVERTURNED", "REMANDED"];

function makeCode(prefix: string): string {
  const sequence = String(Date.now() % 1_000_000).padStart(6, "0");
  return `${prefix}-${new Date().getFullYear()}-${sequence}`;
}

function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function personName(learners: Learner[], learnerId: number): string {
  const learner = learners.find((item) => item.id === learnerId);
  return learner ? `${learner.name} · ${learner.learner_code}` : `Learner #${learnerId}`;
}

function reviewerName(reviewers: Reviewer[], reviewerId: number): string {
  const reviewer = reviewers.find((item) => item.id === reviewerId);
  return reviewer ? reviewer.full_name : `Reviewer #${reviewerId}`;
}

function App() {
  const [section, setSection] = useState<Section>("cases");
  const [workspaceState, setWorkspace] = useState<Workspace | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);
  const [selectedAppealId, setSelectedAppealId] = useState<number | null>(null);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [caseEvidence, setCaseEvidence] = useState<Evidence[]>([]);
  const [caseDecisions, setCaseDecisions] = useState<Decision[]>([]);
  const [decisionDetail, setDecisionDetail] = useState<DecisionDetail | null>(null);
  const [appealDetail, setAppealDetail] = useState<AppealDetail | null>(null);
  const [originalDecision, setOriginalDecision] = useState<DecisionDetail | null>(null);
  const [appealCaseEvidence, setAppealCaseEvidence] = useState<Evidence[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [newSubmissionCode, setNewSubmissionCode] = useState(() => makeCode("SUB"));
  const [newCaseCode, setNewCaseCode] = useState(() => makeCode("CASE"));
  const [selectedEvidenceIds, setSelectedEvidenceIds] = useState<number[]>([]);
  const [detailReloadToken, setDetailReloadToken] = useState(0);
  const workspace = workspaceState ?? emptyWorkspace;

  const loadWorkspace = useCallback(async () => {
    const [learners, assessments, reviewers, submissions, flags, cases, appeals] =
      await Promise.all([
        apiClient.listLearners(),
        apiClient.listAssessments(),
        apiClient.listReviewers(),
        apiClient.listSubmissions(),
        apiClient.listFlags(),
        apiClient.listCases(),
        apiClient.listAppeals(),
      ]);
    setWorkspace({ learners, assessments, reviewers, submissions, flags, cases, appeals });
    setSelectedCaseId((current) =>
      current && cases.some((item) => item.id === current)
        ? current
        : cases[0]?.id ?? null,
    );
    setSelectedAppealId((current) =>
      current && appeals.some((item) => item.id === current)
        ? current
        : appeals[0]?.id ?? null,
    );
    setLoadError(null);
  }, []);

  useEffect(() => {
    void loadWorkspace().catch((error: unknown) => setLoadError(getApiError(error)));
  }, [loadWorkspace]);

  const reload = async () => {
    setRefreshing(true);
    setLoadError(null);
    try {
      await loadWorkspace();
    } catch (error) {
      setLoadError(getApiError(error));
    } finally {
      setRefreshing(false);
    }
  };

  const runMutation = async (
    action: () => Promise<unknown>,
    successMessage: string,
  ) => {
    setBusy(true);
    setNotice(null);
    setLoadError(null);
    try {
      await action();
      setNotice(successMessage);
      await loadWorkspace();
      setDetailReloadToken((token) => token + 1);
    } catch (error) {
      setLoadError(getApiError(error));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    if (selectedCaseId === null) {
      setCaseDetail(null);
      setCaseEvidence([]);
      setCaseDecisions([]);
      setDecisionDetail(null);
      return;
    }
    const controller = new AbortController();
    Promise.all([
      apiClient.getCase(selectedCaseId, controller.signal),
      apiClient.listEvidence(selectedCaseId, controller.signal),
      apiClient.listCaseDecisions(selectedCaseId, controller.signal),
    ])
      .then(([detail, evidence, decisions]) => {
        setCaseDetail(detail);
        setCaseEvidence(evidence);
        setCaseDecisions(decisions);
        setSelectedEvidenceIds([]);
        if (decisions[0]) {
          void apiClient
            .getDecision(decisions[0].id, controller.signal)
            .then(setDecisionDetail)
            .catch((error: unknown) => {
              if (!controller.signal.aborted) {
                setLoadError(getApiError(error));
              }
            });
        } else {
          setDecisionDetail(null);
        }
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setLoadError(getApiError(error));
        }
      });
    return () => controller.abort();
  }, [selectedCaseId, workspace?.cases.length, detailReloadToken]);

  useEffect(() => {
    if (selectedAppealId === null) {
      setAppealDetail(null);
      setOriginalDecision(null);
      setAppealCaseEvidence([]);
      return;
    }
    const controller = new AbortController();
    apiClient
      .getAppeal(selectedAppealId, controller.signal)
      .then(async (detail) => {
        setAppealDetail(detail);
        const decision = await apiClient.getDecision(detail.decision_id, controller.signal);
        setOriginalDecision(decision);
        const evidence = await apiClient.listEvidence(decision.case_id, controller.signal);
        setAppealCaseEvidence(evidence);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setLoadError(getApiError(error));
        }
      });
    return () => controller.abort();
  }, [selectedAppealId, workspace?.appeals.length, detailReloadToken]);

  const selectedCase = useMemo(
    () => workspace?.cases.find((item) => item.id === selectedCaseId) ?? null,
    [workspace?.cases, selectedCaseId],
  );
  const selectedAppeal = useMemo(
    () => workspace?.appeals.find((item) => item.id === selectedAppealId) ?? null,
    [workspace?.appeals, selectedAppealId],
  );

  const submitSubmission = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const learnerId = Number(form.get("learner_id"));
    const assessmentId = Number(form.get("assessment_id"));
    const fileReference = String(form.get("file_reference") ?? "").trim();
    await runMutation(
      async () => {
        await apiClient.createSubmission({
          submission_code: newSubmissionCode,
          learner_id: learnerId,
          assessment_id: assessmentId,
          ...(fileReference ? { file_reference: fileReference } : {}),
        });
        setNewSubmissionCode(makeCode("SUB"));
        formElement.reset();
      },
      "Submission created.",
    );
  };

  const analyzeSubmission = async (submission: Submission) => {
    await runMutation(async () => {
      const result = await apiClient.analyzeSubmission(submission.id);
      setAnalysis(result);
    }, "Similarity analysis completed. A flag is a request for human review, not a finding.");
  };

  const deleteSubmission = async (submission: Submission) => {
    const confirmed = window.confirm(
      `Delete ${submission.submission_code}? Only submissions without analysis or review history can be deleted.`,
    );
    if (!confirmed) return;

    await runMutation(async () => {
      await apiClient.deleteSubmission(submission.id);
      if (analysis?.report.submission_id === submission.id) {
        setAnalysis(null);
      }
    }, "Submission deleted.");
  };

  const createCase = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const flagId = Number(form.get("flag_id"));
    const title = String(form.get("title") ?? "").trim();
    const description = String(form.get("description") ?? "").trim();
    await runMutation(async () => {
      const created = await apiClient.createCase({
        case_code: newCaseCode,
        flag_id: flagId,
        title,
        ...(description ? { description } : {}),
      });
      setSelectedCaseId(created.id);
      setNewCaseCode(makeCode("CASE"));
      formElement.reset();
    }, "Case opened from the selected similarity flag.");
  };

  const createAppeal = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedCase) {
      return;
    }
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const decisionId = Number(form.get("decision_id"));
    const grounds = String(form.get("grounds") ?? "").trim();
    await runMutation(async () => {
      const created = await apiClient.createAppeal({
        decision_id: decisionId,
        learner_id: selectedCase.learner_id,
        grounds,
      });
      setSelectedAppealId(created.id);
      setSection("appeals");
      formElement.reset();
    }, "Appeal submitted as a separate review record.");
  };

  if (!workspaceState && section !== "data" && !loadError) {
    return (
      <main className="loading-screen">
        <LoaderCircle aria-hidden="true" className="spin" size={24} />
        <p>Connecting to the case-management API…</p>
      </main>
    );
  }

  if (!workspaceState && section !== "data") {
    return (
      <main className="connection-screen">
        <div className="connection-card">
          <div className="brand-mark"><ShieldCheck size={23} /></div>
          <p className="eyebrow">Academic integrity casework</p>
          <h1>Backend connection unavailable</h1>
          <p className="muted">
            This workspace reads and updates records through the backend API.
            Start the FastAPI service, then retry.
          </p>
          <div className="error-box" role="alert">{loadError}</div>
          <button className="button button-primary" onClick={() => void reload()} type="button">
            <RefreshCw size={16} /> Retry connection
          </button>
          <button className="button button-secondary" onClick={() => setSection("data")} type="button">
            <Database size={16} /> Open dataset tools
          </button>
        </div>
      </main>
    );
  }

  const activeReviewers = workspace.reviewers.filter((reviewer) => reviewer.status === "ACTIVE");
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="Academic integrity casework home">
          <span className="brand-mark"><ShieldCheck size={22} /></span>
          <span>
            <strong>Integrity Office</strong>
            <small>Casework workspace</small>
          </span>
        </a>
        <div className="sidebar-label">WORKFLOWS & DATA</div>
        <nav className="nav-list" aria-label="Workflow sections">
          <NavItem
            active={section === "cases"}
            count={workspace.cases.filter((item) => item.status !== "CLOSED").length}
            icon={<FolderKanban size={18} />}
            label="Casework"
            onClick={() => setSection("cases")}
          />
          <NavItem
            active={section === "appeals"}
            count={workspace.appeals.filter((item) => item.status !== "DECIDED" && item.status !== "WITHDRAWN").length}
            icon={<Scale size={18} />}
            label="Appeals"
            onClick={() => setSection("appeals")}
          />
          <NavItem
            active={section === "submissions"}
            count={workspace.submissions.length}
            icon={<FilePlus2 size={18} />}
            label="Submissions"
            onClick={() => setSection("submissions")}
          />
          <NavItem
            active={section === "data"}
            icon={<Database size={18} />}
            label="Dataset tools"
            onClick={() => setSection("data")}
          />
        </nav>
        <div className="sidebar-bottom">
          <span className={`connection-dot ${workspaceState ? "" : "connection-dot-offline"}`} />
          <span>{workspaceState ? "Connected to backend" : "Workflow connection unavailable"}</span>
          <small>API · {import.meta.env.VITE_API_BASE_URL ?? "localhost:8000"}</small>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <p className="eyebrow">Academic Integrity Management System</p>
            <h1>{sectionLabels[section]}</h1>
          </div>
          <button
            className="button button-quiet"
            disabled={refreshing || busy}
            onClick={() => void reload()}
            type="button"
          >
            <RefreshCw className={refreshing ? "spin" : ""} size={16} />
            Refresh records
          </button>
        </header>

        <div className="due-process-note">
          <ShieldCheck size={18} />
          <span>A similarity flag starts a human review; it does not establish misconduct.</span>
        </div>
        {notice && <div className="notice-box" role="status"><Check size={16} />{notice}</div>}
        {loadError && section !== "data" && <div className="error-box inline-error" role="alert"><AlertCircle size={16} />{loadError}</div>}

        {section === "data" && <DataLab />}
        {section === "cases" && (
          <section className="workflow-layout">
            <div className="primary-column">
              <PanelHeader
                title="Review cases"
                description="Select a case to inspect its evidence, assignments, decision, and event history."
                count={workspace.cases.length}
              />
              <div className="record-list">
                {workspace.cases.length === 0 ? (
                  <EmptyState title="No cases yet" text="Open a case from a similarity flag when human review is required." />
                ) : workspace.cases.map((item) => (
                  <button
                    className={`record-row ${selectedCaseId === item.id ? "record-row-active" : ""}`}
                    key={item.id}
                    onClick={() => setSelectedCaseId(item.id)}
                    type="button"
                  >
                    <span className="record-icon"><FolderKanban size={17} /></span>
                    <span className="record-main">
                      <strong>{item.case_code}</strong>
                      <small>{item.title} · {personName(workspace.learners, item.learner_id)}</small>
                    </span>
                    <StatusPill value={item.status} />
                  </button>
                ))}
              </div>
              <form className="form-card compact-form" onSubmit={(event) => void createCase(event)}>
                <h3>Open a case</h3>
                <p className="muted">Create a case from a flag; the backend prevents relinking a flag already under review.</p>
                <div className="form-grid">
                  <label>
                    Flag
                    <select name="flag_id" required defaultValue="">
                      <option value="" disabled>Select a similarity flag</option>
                      {workspace.flags.map((flag) => (
                        <option key={flag.id} value={flag.id}>
                          {flag.flag_code} · {flag.flag_type} · submission #{flag.submission_id}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Case code
                    <input
                      name="case_code"
                      pattern="CASE-\d{4}-\d{6}"
                      required
                      value={newCaseCode}
                      onChange={(event) => setNewCaseCode(event.target.value)}
                    />
                  </label>
                  <label className="field-wide">
                    Case title
                    <input name="title" minLength={3} maxLength={250} required placeholder="Describe the review matter" />
                  </label>
                  <label className="field-wide">
                    Description
                    <textarea name="description" rows={2} placeholder="Optional context" />
                  </label>
                </div>
                <button className="button button-primary" disabled={busy || workspace.flags.length === 0} type="submit">
                  <FolderKanban size={16} /> Open case
                </button>
              </form>
            </div>

            <div className="secondary-column">
              {!selectedCase ? (
                <EmptyState title="Choose a case" text="Case details and available actions will appear here." />
              ) : (
                <CaseWorkspace
                  activeReviewers={activeReviewers}
                  busy={busy}
                  caseDecisions={caseDecisions}
                  caseDetail={caseDetail}
                  caseEvidence={caseEvidence}
                  decisionDetail={decisionDetail}
                  learners={workspace.learners}
                  reviewers={workspace.reviewers}
                  selectedCase={selectedCase}
                  selectedEvidenceIds={selectedEvidenceIds}
                  setSelectedEvidenceIds={setSelectedEvidenceIds}
                  onAction={runMutation}
                  onAppeal={createAppeal}
                />
              )}
            </div>
          </section>
        )}

        {section === "appeals" && (
          <section className="workflow-layout">
            <div className="primary-column">
              <PanelHeader
                title="Appeal reviews"
                description="Appeals are separate records and must be reviewed independently from the original decision."
                count={workspace.appeals.length}
              />
              <div className="record-list">
                {workspace.appeals.length === 0 ? (
                  <EmptyState title="No appeals yet" text="A learner can appeal a recorded case decision from the casework view." />
                ) : workspace.appeals.map((appeal) => (
                  <button
                    className={`record-row ${selectedAppealId === appeal.id ? "record-row-active" : ""}`}
                    key={appeal.id}
                    onClick={() => setSelectedAppealId(appeal.id)}
                    type="button"
                  >
                    <span className="record-icon appeal-icon"><Scale size={17} /></span>
                    <span className="record-main">
                      <strong>{appeal.appeal_code}</strong>
                      <small>{personName(workspace.learners, appeal.learner_id)} · decision #{appeal.decision_id}</small>
                    </span>
                    <StatusPill value={appeal.status} />
                  </button>
                ))}
              </div>
            </div>
            <div className="secondary-column">
              {selectedAppeal ? (
                <AppealWorkspace
                  activeReviewers={activeReviewers}
                  appeal={selectedAppeal}
                  detail={appealDetail}
                  caseEvidence={appealCaseEvidence}
                  learners={workspace.learners}
                  originalDecision={originalDecision}
                  reviewers={workspace.reviewers}
                  busy={busy}
                  onAction={runMutation}
                />
              ) : (
                <EmptyState title="Choose an appeal" text="Assignment, resolution, and appeal history appear here." />
              )}
            </div>
          </section>
        )}

        {section === "submissions" && (
          <section className="workflow-layout submissions-layout">
            <div className="primary-column">
              <PanelHeader
                title="Submissions"
                description="Register submissions and run similarity analysis. Only unanalysed submissions without review history can be deleted."
                count={workspace.submissions.length}
              />
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr><th>Submission</th><th>Learner</th><th>Assessment</th><th>Status</th><th /></tr>
                  </thead>
                  <tbody>
                    {workspace.submissions.map((submission) => (
                      <tr key={submission.id}>
                        <td><strong>{submission.submission_code}</strong><small>Received {formatDate(submission.submitted_at)}</small></td>
                        <td>{personName(workspace.learners, submission.learner_id)}</td>
                        <td>{workspace.assessments.find((item) => item.id === submission.assessment_id)?.title ?? `Assessment #${submission.assessment_id}`}</td>
                        <td><StatusPill value={submission.status} /></td>
                        <td>
                          <div className="submission-row-actions">
                            <button
                              className="button button-small button-outline"
                              disabled={busy}
                              onClick={() => void analyzeSubmission(submission)}
                              type="button"
                            >
                              Analyze <ArrowUpRight size={14} />
                            </button>
                            <button
                              aria-label={`Delete ${submission.submission_code}`}
                              className="button button-small button-delete"
                              disabled={busy}
                              onClick={() => void deleteSubmission(submission)}
                              title="Delete unanalysed submission"
                              type="button"
                            >
                              <Trash2 size={14} /> Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {workspace.submissions.length === 0 && (
                      <tr><td colSpan={5}><EmptyState title="No submissions" text="Create a submission to start the review workflow." /></td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              {analysis && (
                <div className="analysis-result">
                  <div className="analysis-topline">
                    <div>
                      <p className="eyebrow">Latest analysis · {analysis.report.report_code}</p>
                      <h3>{analysis.report.overall_score}% similarity · {analysis.rule_action.replaceAll("_", " ")}</h3>
                    </div>
                    {analysis.flag_created && analysis.flag && <StatusPill value={`FLAG ${analysis.flag.flag_code}`} />}
                  </div>
                  <div className="score-breakdown">
                    <span>Quoted material <strong>{analysis.report.quotation_percentage}%</strong></span>
                    <span>Shared template <strong>{analysis.report.template_percentage}%</strong></span>
                    <span>Internet matches <strong>{analysis.report.internet_percentage}%</strong></span>
                  </div>
                  <p className="muted">{analysis.due_process_notice}</p>
                </div>
              )}
            </div>
            <form className="form-card create-submission" onSubmit={(event) => void submitSubmission(event)}>
              <h3>Register submission</h3>
              <p className="muted">Creates a backend record linked to an existing learner and assessment.</p>
              <label>
                Submission code
                <input
                  pattern="SUB-\d{4}-\d{6}"
                  required
                  value={newSubmissionCode}
                  onChange={(event) => setNewSubmissionCode(event.target.value)}
                />
              </label>
              <label>
                Learner
                <select name="learner_id" required defaultValue="">
                  <option value="" disabled>Select a learner</option>
                  {workspace.learners.map((learner) => (
                    <option key={learner.id} value={learner.id}>
                      {learner.learner_code} · {learner.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Assessment
                <select name="assessment_id" required defaultValue="">
                  <option value="" disabled>Select an assessment</option>
                  {workspace.assessments.map((assessment) => (
                    <option key={assessment.id} value={assessment.id}>
                      {assessment.assessment_code} · {assessment.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                File reference
                <input name="file_reference" placeholder="Optional URL or storage reference" />
              </label>
              <button
                className="button button-primary"
                disabled={busy || workspace.learners.length === 0 || workspace.assessments.length === 0}
                type="submit"
              >
                <FilePlus2 size={16} /> Create submission
              </button>
            </form>
          </section>
        )}
      </main>
    </div>
  );
}

interface NavItemProps {
  active: boolean;
  count?: number;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}

function NavItem({ active, count, icon, label, onClick }: NavItemProps) {
  return (
    <button className={`nav-item ${active ? "nav-item-active" : ""}`} onClick={onClick} type="button">
      {icon}<span>{label}</span>{count !== undefined && <small>{count}</small>}
    </button>
  );
}

function PanelHeader({ title, description, count }: { title: string; description: string; count: number }) {
  return (
    <div className="panel-header">
      <div>
        <h2>{title}</h2>
        <p className="muted">{description}</p>
      </div>
      <span className="count-badge">{count}</span>
    </div>
  );
}

function StatusPill({ value }: { value: string }) {
  const normalized = value.toLowerCase().replaceAll("_", "-");
  return <span className={`status-pill status-${normalized}`}>{value.replaceAll("_", " ")}</span>;
}

function EmptyState({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><strong>{title}</strong><p>{text}</p></div>;
}

interface CaseWorkspaceProps {
  activeReviewers: Reviewer[];
  busy: boolean;
  caseDecisions: Decision[];
  caseDetail: CaseDetail | null;
  caseEvidence: Evidence[];
  decisionDetail: DecisionDetail | null;
  learners: Learner[];
  reviewers: Reviewer[];
  selectedCase: CaseRecord;
  selectedEvidenceIds: number[];
  setSelectedEvidenceIds: (ids: number[]) => void;
  onAction: (action: () => Promise<unknown>, message: string) => Promise<void>;
  onAppeal: (event: FormEvent<HTMLFormElement>) => Promise<void>;
}

function CaseWorkspace({
  activeReviewers,
  busy,
  caseDecisions,
  caseDetail,
  caseEvidence,
  decisionDetail,
  learners,
  reviewers,
  selectedCase,
  selectedEvidenceIds,
  setSelectedEvidenceIds,
  onAction,
  onAppeal,
}: CaseWorkspaceProps) {
  const activeAssignments = caseDetail?.assignments.filter(
    (assignment) => assignment.status === "ACTIVE" && assignment.conflict_status === "CLEARED",
  ) ?? [];
  const currentReviewerId = activeAssignments[0]?.reviewer_id;
  const availableDecisions = caseDecisions;

  const submitAssignment = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const reviewerId = Number(new FormData(event.currentTarget).get("reviewer_id"));
    void onAction(
      () => apiClient.assignCase(selectedCase.id, reviewerId),
      "Independent case reviewer assigned.",
    );
  };

  const submitStatus = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    void onAction(
      () => apiClient.updateCaseStatus(
        selectedCase.id,
        String(form.get("status")),
        String(form.get("reason") ?? ""),
      ),
      "Case status updated and recorded.",
    );
  };

  const submitEvidence = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const title = String(form.get("title") ?? "").trim();
    const evidenceType = String(form.get("evidence_type") ?? "OTHER");
    const sourceReference = String(form.get("source_reference") ?? "").trim();
    void onAction(
      () => apiClient.createEvidence({
        case_id: selectedCase.id,
        evidence_type: evidenceType,
        title,
        ...(sourceReference ? { source_reference: sourceReference } : {}),
      }),
      "Evidence appended to the case record.",
    );
    formElement.reset();
  };

  const submitDecision = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const reviewerId = Number(form.get("reviewer_id"));
    const outcome = String(form.get("outcome"));
    const rationale = String(form.get("rationale") ?? "").trim();
    void onAction(
      () => apiClient.createDecision({
        case_id: selectedCase.id,
        reviewer_id: reviewerId,
        outcome,
        rationale,
        evidence_ids: selectedEvidenceIds,
      }),
      "Decision recorded with an immutable evidence snapshot.",
    );
  };

  const toggleEvidence = (evidenceId: number, checked: boolean) => {
    setSelectedEvidenceIds(
      checked
        ? [...new Set([...selectedEvidenceIds, evidenceId])]
        : selectedEvidenceIds.filter((id) => id !== evidenceId),
    );
  };

  return (
    <article className="detail-card">
      <div className="detail-heading">
        <div>
          <p className="eyebrow">{selectedCase.case_code}</p>
          <h2>{selectedCase.title}</h2>
          <p className="muted">{personName(learners, selectedCase.learner_id)}</p>
        </div>
        <StatusPill value={selectedCase.status} />
      </div>
      {selectedCase.description && <p className="detail-description">{selectedCase.description}</p>}

      <section className="detail-section">
        <h3><Gavel size={16} /> Reviewer assignment and status</h3>
        <div className="action-grid">
          <form onSubmit={submitAssignment}>
            <label>
              Assign reviewer
              <select name="reviewer_id" required defaultValue="">
                <option value="" disabled>Select an active reviewer</option>
                {activeReviewers.map((reviewer) => (
                  <option key={reviewer.id} value={reviewer.id}>{reviewer.full_name} · {reviewer.reviewer_code}</option>
                ))}
              </select>
            </label>
            <button className="button button-outline" disabled={busy || activeReviewers.length === 0} type="submit">Assign</button>
          </form>
          <form onSubmit={submitStatus}>
            <label>
              Move case to
              <select name="status" required defaultValue="">
                <option value="" disabled>Select next status</option>
                {(nextCaseStatuses[selectedCase.status] ?? []).map((status) => (
                  <option key={status} value={status}>{status.replaceAll("_", " ")}</option>
                ))}
              </select>
            </label>
            <input name="reason" placeholder="Reason for status change" />
            <button
              className="button button-outline"
              disabled={busy || (nextCaseStatuses[selectedCase.status] ?? []).length === 0}
              type="submit"
            >
              Update status
            </button>
          </form>
        </div>
        {caseDetail?.assignments.map((assignment) => (
          <div className="assignment-line" key={assignment.id}>
            <span>{reviewerName(reviewers, assignment.reviewer_id)}</span>
            <StatusPill value={`${assignment.status} · ${assignment.conflict_status}`} />
          </div>
        ))}
      </section>

      <section className="detail-section">
        <h3>Evidence record <span className="subtle-count">{caseEvidence.length}</span></h3>
        <div className="evidence-list">
          {caseEvidence.map((item) => (
            <label className="evidence-row" key={item.id}>
              <input
                checked={selectedEvidenceIds.includes(item.id)}
                onChange={(event) => toggleEvidence(item.id, event.target.checked)}
                type="checkbox"
              />
              <span><strong>{item.evidence_code} · {item.title}</strong><small>{item.evidence_type} · added {formatDate(item.added_at)}</small></span>
            </label>
          ))}
          {caseEvidence.length === 0 && <p className="muted">No evidence has been added.</p>}
        </div>
        <form className="inline-form" onSubmit={submitEvidence}>
          <select name="evidence_type" aria-label="Evidence type" defaultValue="DOCUMENT">
            {["DOCUMENT", "SUBMISSION_VERSION", "EXPLANATION", "SIMILARITY_REPORT", "OTHER"].map((item) => (
              <option key={item} value={item}>{item.replaceAll("_", " ")}</option>
            ))}
          </select>
          <input name="title" required placeholder="Evidence title" />
          <input name="source_reference" placeholder="Optional source reference" />
          <button className="button button-outline" disabled={busy} type="submit">Add evidence</button>
        </form>
      </section>

      <section className="detail-section">
        <h3>Record decision</h3>
        {caseDecisions.length > 0 ? (
          caseDecisions.map((decision) => (
            <div className="decision-card" key={decision.id}>
              <div><strong>{decision.outcome.replaceAll("_", " ")}</strong><small>{decision.decision_code} · {reviewerName(reviewers, decision.reviewer_id)}</small></div>
              <p>{decision.rationale}</p>
              <div className="snapshot-list">
                <strong>Evidence snapshot</strong>
                {(decisionDetail?.evidence_snapshot ?? []).map((snapshot) => (
                  <small key={snapshot.id}>
                    {snapshot.evidence_code_snapshot} · {snapshot.evidence_title_snapshot}
                  </small>
                ))}
                {!decisionDetail?.evidence_snapshot.length && <small>No evidence snapshot attached.</small>}
              </div>
            </div>
          ))
        ) : (
          <form className="decision-form" onSubmit={submitDecision}>
            <label>
              Assigned reviewer
              <select name="reviewer_id" required defaultValue={currentReviewerId ?? ""}>
                <option value="" disabled>Select a cleared active assignment</option>
                {activeAssignments.map((assignment) => (
                  <option key={assignment.id} value={assignment.reviewer_id}>
                    {reviewerName(reviewers, assignment.reviewer_id)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Outcome
              <select name="outcome" required defaultValue="">
                <option value="" disabled>Select outcome</option>
                {decisionOutcomes.map((outcome) => <option key={outcome} value={outcome}>{outcome.replaceAll("_", " ")}</option>)}
              </select>
            </label>
            <label className="field-wide">
              Rationale
              <textarea name="rationale" minLength={1} required rows={3} placeholder="Record the evidence-based reasoning" />
            </label>
            <p className="form-help">Selected evidence above is saved as an immutable snapshot with this decision.</p>
            {selectedCase.status !== "DECISION_PENDING" && (
              <p className="form-help">Move the case to DECISION PENDING before recording a decision.</p>
            )}
            <button
              className="button button-primary"
              disabled={busy || activeAssignments.length === 0 || selectedCase.status !== "DECISION_PENDING"}
              type="submit"
            >
              Record decision
            </button>
          </form>
        )}
      </section>

      {availableDecisions.length > 0 && (
        <section className="detail-section">
          <h3>Submit an appeal</h3>
          <p className="form-help">The original decision is preserved. An appeal creates a separate record and independent review.</p>
          <form className="appeal-create-form" onSubmit={(event) => void onAppeal(event)}>
            <label>
              Decision to appeal
              <select name="decision_id" required defaultValue="">
                <option value="" disabled>Select decision</option>
                {availableDecisions.map((decision) => (
                  <option key={decision.id} value={decision.id}>
                    {decision.decision_code} · {decision.outcome.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Grounds
              <textarea name="grounds" required minLength={10} maxLength={10000} rows={3} placeholder="Explain why the original decision should be reviewed" />
            </label>
            <button className="button button-outline" disabled={busy} type="submit">Submit appeal</button>
          </form>
        </section>
      )}

      <section className="detail-section">
        <h3>Case timeline</h3>
        <ol className="timeline">
          {(caseDetail?.events ?? []).map((item) => (
            <li key={item.id}>
              <span className="timeline-dot" />
              <div><strong>{item.event_type.replaceAll("_", " ")}</strong><small>{item.description}</small><time>{formatDate(item.created_at)}</time></div>
            </li>
          ))}
          {!caseDetail?.events.length && <li className="muted">Loading case history…</li>}
        </ol>
      </section>
    </article>
  );
}

interface AppealWorkspaceProps {
  activeReviewers: Reviewer[];
  appeal: Appeal;
  caseEvidence: Evidence[];
  detail: AppealDetail | null;
  learners: Learner[];
  originalDecision: DecisionDetail | null;
  reviewers: Reviewer[];
  busy: boolean;
  onAction: (action: () => Promise<unknown>, message: string) => Promise<void>;
}

function AppealWorkspace({
  activeReviewers,
  appeal,
  caseEvidence,
  detail,
  learners,
  originalDecision,
  reviewers,
  busy,
  onAction,
}: AppealWorkspaceProps) {
  const independentReviewers = activeReviewers.filter(
    (reviewer) => reviewer.id !== originalDecision?.reviewer_id,
  );

  const assignReviewer = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const reviewerId = Number(new FormData(event.currentTarget).get("reviewer_id"));
    void onAction(
      () => apiClient.assignAppeal(appeal.id, reviewerId),
      "Independent appeal reviewer assigned.",
    );
  };

  const resolveAppeal = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const reviewerId = Number(form.get("reviewer_id"));
    const outcome = String(form.get("outcome"));
    const rationale = String(form.get("rationale") ?? "").trim();
    void onAction(
      () => apiClient.resolveAppeal(appeal.id, reviewerId, outcome, rationale),
      "Appeal resolved. The original decision remains unchanged.",
    );
  };

  const addEvidence = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const evidenceId = Number(new FormData(event.currentTarget).get("evidence_id"));
    void onAction(
      () => apiClient.addAppealEvidence(appeal.id, evidenceId),
      "Evidence appended to the appeal record.",
    );
    event.currentTarget.reset();
  };

  return (
    <article className="detail-card">
      <div className="detail-heading">
        <div>
          <p className="eyebrow">{appeal.appeal_code}</p>
          <h2>Independent appeal review</h2>
          <p className="muted">{personName(learners, appeal.learner_id)} · Decision #{appeal.decision_id}</p>
        </div>
        <StatusPill value={appeal.status} />
      </div>
      <section className="decision-card original-decision">
        <p className="eyebrow">Original decision · unchanged</p>
        {originalDecision ? (
          <>
            <strong>{originalDecision.outcome.replaceAll("_", " ")}</strong>
            <small>{originalDecision.decision_code} · {reviewerName(reviewers, originalDecision.reviewer_id)}</small>
            <p>{originalDecision.rationale}</p>
          </>
        ) : <p className="muted">Loading original decision…</p>}
      </section>
      <section className="detail-section">
        <h3>Appeal grounds</h3>
        <p className="grounds-text">{appeal.grounds}</p>
      </section>
      <section className="detail-section">
        <h3>Appeal evidence <span className="subtle-count">{detail?.evidence_snapshots.length ?? 0}</span></h3>
        <div className="evidence-list">
          {(detail?.evidence_snapshots ?? []).map((snapshot) => (
            <div className="evidence-row" key={snapshot.id}>
              <span><strong>{snapshot.evidence_code_snapshot} · {snapshot.evidence_title_snapshot}</strong><small>{snapshot.evidence_type_snapshot} · added {formatDate(snapshot.added_at)}</small></span>
            </div>
          ))}
          {!detail?.evidence_snapshots.length && <p className="muted">No additional evidence is attached to this appeal.</p>}
        </div>
        {["SUBMITTED", "UNDER_REVIEW"].includes(appeal.status) && (
          <form className="inline-form appeal-evidence-form" onSubmit={addEvidence}>
            <select name="evidence_id" required defaultValue="" aria-label="Select case evidence">
              <option value="" disabled>Select evidence from original case</option>
              {caseEvidence.map((item) => <option key={item.id} value={item.id}>{item.evidence_code} · {item.title}</option>)}
            </select>
            <button className="button button-outline" disabled={busy || caseEvidence.length === 0} type="submit">Add to appeal</button>
          </form>
        )}
      </section>
      {appeal.status === "SUBMITTED" && (
        <form className="action-form" onSubmit={assignReviewer}>
          <label>
            Assign independent reviewer
            <select name="reviewer_id" required defaultValue="">
              <option value="" disabled>Select reviewer</option>
              {independentReviewers.map((reviewer) => (
                <option key={reviewer.id} value={reviewer.id}>
                  {reviewer.full_name} · {reviewer.reviewer_code}
                </option>
              ))}
            </select>
          </label>
          <p className="form-help">The backend rejects the original decision-maker and reviewers with conflicts.</p>
          <button className="button button-primary" disabled={busy || independentReviewers.length === 0} type="submit">Assign reviewer</button>
        </form>
      )}
      {appeal.status === "UNDER_REVIEW" && (
        <form className="action-form" onSubmit={resolveAppeal}>
          <label>
            Independent reviewer
            <select name="reviewer_id" required defaultValue={appeal.assigned_reviewer_id ?? ""}>
              {appeal.assigned_reviewer_id ? (
                <option value={appeal.assigned_reviewer_id}>
                  {reviewerName(reviewers, appeal.assigned_reviewer_id)}
                </option>
              ) : <option value="" disabled>No assigned reviewer</option>}
            </select>
          </label>
          <label>
            Outcome
            <select name="outcome" required defaultValue="">
              <option value="" disabled>Select outcome</option>
              {appealOutcomes.map((outcome) => <option key={outcome} value={outcome}>{outcome}</option>)}
            </select>
          </label>
          <label>
            Rationale
            <textarea name="rationale" required minLength={10} rows={3} placeholder="Explain the independent review outcome" />
          </label>
          <button className="button button-primary" disabled={busy} type="submit">Resolve appeal</button>
        </form>
      )}
      {appeal.outcome && (
        <section className="outcome-panel">
          <p className="eyebrow">Appeal outcome · {appeal.outcome}</p>
          <p>{appeal.outcome_rationale}</p>
          <small>Resolved {formatDate(appeal.resolved_at)}</small>
        </section>
      )}
      <section className="detail-section">
        <h3>Appeal history</h3>
        <ol className="timeline">
          {(detail?.events ?? []).map((event) => (
            <li key={event.id}>
              <span className="timeline-dot" />
              <div><strong>{event.event_type.replaceAll("_", " ")}</strong><small>{event.description}</small><time>{formatDate(event.created_at)}</time></div>
            </li>
          ))}
          {!detail?.events.length && <li className="muted">Loading appeal history…</li>}
        </ol>
      </section>
    </article>
  );
}

export default App;
