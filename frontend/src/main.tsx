import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  LayoutDashboard,
  CircleDot,
  List,
  Folder,
  CircleCheck,
  ClipboardCheck,
  History,
  Search,
  LogOut,
  Menu,
  X,
  Plus,
  ArrowRight,
  ArrowLeft,
  Download,
  Upload,
  ShieldCheck,
  Eye,
  EyeOff,
  FileText,
  Printer,
} from "lucide-react";
import { api, post } from "./api";
import "@fontsource-variable/inter";
import type {
  User,
  Cycle,
  Summary,
  Area,
  Requirement,
  Document,
  Submission,
  Item,
  Audit,
  Certification,
  SearchResults,
  ComplianceReport,
} from "./types";
import "./styles.css";

const labels: Record<string, string> = {
  complete: "Complete",
  ready_for_completion_review: "Ready for Completion Review",
  reopened: "Reopened",
  approved: "Approved",
  pending: "For Verification",
  for_compliance: "For Compliance",
  missing: "Missing Evidence",
  revision_requested: "Revision Requested",
  rejected: "Rejected",
  expired: "Expired",
  excluded: "Not Applicable",
  draft: "Draft",
};
const date = (value: string | null) =>
  value
    ? new Date(
        value.length === 10 ? value + "T00:00:00" : value,
      ).toLocaleDateString("en-PH", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "No deadline";
const dateTime = (value: string) =>
  new Date(value).toLocaleString("en-PH", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
const percent = (value: number | null) =>
  value === null ? "N/A" : `${value}%`;
const initials = (name: string) =>
  name
    .split(" ")
    .map((n) => n[0])
    .slice(0, 2)
    .join("");
function Badge({ status }: { status: string }) {
  return <span className={`badge ${status}`}>{labels[status] || status}</span>;
}
function Progress({ value }: { value: number | null }) {
  return (
    <div className="progress">
      <span style={{ width: `${value || 0}%` }} />
    </div>
  );
}
function ErrorBox({ error }: { error: string }) {
  return error ? (
    <div className="error" role="alert">
      {error}
    </div>
  ) : null;
}

function Modal({
  title,
  children,
  close,
}: {
  title: string;
  children: React.ReactNode;
  close: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog ref={ref} onCancel={close}>
      <div className="modal-heading">
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close dialog"
          onClick={close}
        >
          <X size={20} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

function Login({
  onLogin,
  message,
}: {
  onLogin: (u: User) => void;
  message: string;
}) {
  const [error, setError] = useState(message),
    [busy, setBusy] = useState(false),
    [show, setShow] = useState(false);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      onLogin(
        await post<User>("auth/login/", {
          username: f.get("username"),
          password: f.get("password"),
          remember: f.get("remember") === "on",
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-story">
        <div className="school-brand">
          <span className="logo">MC</span>
          <strong>Mabini Colleges, Inc.</strong>
        </div>
        <div className="story-content">
          <h1>
            Graduate School
            <br />
            Accreditation Hub
          </h1>
          <p>
            A centralized digital repository and compliance management platform
            supporting PACUCOA accreditation and quality assurance activities.
          </p>
          <div className="features">
            <div>
              🏛️ <span>Centralized Evidence Repository</span>
            </div>
            <div>
              ✅ <span>Compliance Monitoring</span>
            </div>
            <div>
              🔎 <span>Evidence Verification</span>
            </div>
            <div>
              📈 <span>Accreditation Readiness</span>
            </div>
          </div>
        </div>
        <footer>
          © {new Date().getFullYear()} Mabini Colleges, Inc. — Institution-Owned
          System
        </footer>
      </section>
      <section className="login-card">
        <span className="logo large">MC</span>
        <h2>MC Accreditation Hub</h2>
        <p>Graduate School Accreditation Management</p>
        <form onSubmit={submit}>
          <ErrorBox error={error} />
          <label>
            Email / Username
            <input name="username" autoComplete="username" required />
          </label>
          <label>
            Password
            <div className="password-field">
              <input
                name="password"
                type={show ? "text" : "password"}
                autoComplete="current-password"
                required
              />
              <button
                type="button"
                className="icon-button"
                aria-label={show ? "Hide password" : "Show password"}
                onClick={() => setShow(!show)}
              >
                {show ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </label>
          <label className="check">
            <input name="remember" type="checkbox" />
            Remember me for 8 hours
          </label>
          <button className="primary full" disabled={busy}>
            {busy ? "Signing in…" : "Sign In"}
          </button>
        </form>
        <small>Institution-Owned System · Mabini Colleges, Inc.</small>
      </section>
    </main>
  );
}

const nav = [
  ["dashboard", "Dashboard", LayoutDashboard],
  ["areas", "Accreditation Areas", CircleDot],
  ["requirements", "Requirements", List],
  ["documents", "Evidence Repository", Folder],
  ["reviews", "Evidence Verification", ClipboardCheck],
  ["compliance", "Compliance Monitoring", CircleCheck],
  ["search", "Search", Search],
  ["reports", "Reports", FileText],
  ["audit", "Audit Trail", History],
] as const;
const subtitles: Record<string, string> = {
  dashboard: "Graduate School Accreditation Dashboard",
  areas: "Manage and monitor accreditation area categories",
  requirements: "All requirements and evidence status",
  documents: "Digital repository of accreditation documents",
  reviews: "Review submitted evidence and record decisions",
  compliance: "Track compliance across all accreditation areas",
  search: "Find requirements and evidence you are authorized to access",
  reports: "Printable compliance summaries and CSV export",
  audit: "System activity and change log",
};

function App() {
  const [user, setUser] = useState<User | null>(null),
    [initializing, setInitializing] = useState(true),
    [sessionMessage, setSessionMessage] = useState("");
  const [page, setPage] = useState("dashboard"),
    [mobile, setMobile] = useState(false);
  const [cycles, setCycles] = useState<Cycle[]>([]),
    [cycle, setCycle] = useState(""),
    [areas, setAreas] = useState<Area[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]),
    [documents, setDocuments] = useState<Document[]>([]),
    [submissions, setSubmissions] = useState<Submission[]>([]),
    [events, setEvents] = useState<Audit[]>([]),
    [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState(""),
    [loading, setLoading] = useState(false),
    [notice, setNotice] = useState(""),
    [search, setSearch] = useState(""),
    [areaFilter, setAreaFilter] = useState(""),
    [statusFilter, setStatusFilter] = useState("");
  const [searchTerm, setSearchTerm] = useState(""),
    [searchResults, setSearchResults] = useState<SearchResults | null>(null),
    [searchLoading, setSearchLoading] = useState(false),
    [searchError, setSearchError] = useState("");
  const [reportArea, setReportArea] = useState(""),
    [reportStatus, setReportStatus] = useState(""),
    [report, setReport] = useState<ComplianceReport | null>(null),
    [reportLoading, setReportLoading] = useState(false),
    [reportError, setReportError] = useState("");
  const [detail, setDetail] = useState<Requirement | null>(null),
    [docDetail, setDocDetail] = useState<Document | null>(null);
  const [requirementForm, setRequirementForm] = useState(false),
    [editing, setEditing] = useState<Requirement | null>(null);
  const [upload, setUpload] = useState<{
      doc?: Document;
      item?: Item;
      area?: number;
    } | null>(null),
    [mappingItem, setMappingItem] = useState<Item | null>(null),
    [review, setReview] = useState<Submission | null>(null),
    [certification, setCertification] = useState<{
      requirement: Requirement;
      outcome: "complete" | "reopened";
    } | null>(null);
  const requestGeneration = useRef(0);
  function clearWorkspace() {
    requestGeneration.current += 1;
    setCycle("");
    setCycles([]);
    setAreas([]);
    setRequirements([]);
    setDocuments([]);
    setSubmissions([]);
    setEvents([]);
    setSummary(null);
    setDetail(null);
    setDocDetail(null);
    setUpload(null);
    setReview(null);
    setCertification(null);
    setMappingItem(null);
    setRequirementForm(false);
    setLoading(false);
    setError("");
    setNotice("");
    setSearchResults(null);
    setSearchError("");
    setReport(null);
    setReportError("");
  }
  useEffect(() => {
    api<User>("auth/me/")
      .then(setUser)
      .catch(() => {})
      .finally(() => setInitializing(false));
    const expired = () => {
      clearWorkspace();
      setUser(null);
      setSessionMessage("Your session expired. Please sign in again.");
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, []);
  useEffect(() => {
    let active = true;
    if (user) {
      api<Cycle[]>("cycles/")
        .then((c) => {
          if (!active) return;
          setCycles(c);
          setCycle(c[0] ? String(c[0].id) : "");
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    }
    return () => {
      active = false;
    };
  }, [user]);
  async function refresh(includeDetails = true) {
    if (!cycle) return;
    const generation = ++requestGeneration.current;
    setLoading(true);
    setError("");
    try {
      const suffix = `?cycle=${cycle}`;
      const [a, r, d, s, c, ev] = await Promise.all([
        api<Area[]>("areas/" + suffix),
        api<Requirement[]>("requirements/" + suffix),
        api<Document[]>("documents/" + suffix),
        api<Submission[]>("submissions/" + suffix),
        api<Summary>("compliance/" + suffix),
        api<Audit[]>("audit/" + suffix),
      ]);
      if (generation !== requestGeneration.current) return;
      setAreas(a);
      setRequirements(r);
      setDocuments(d);
      setSubmissions(s);
      setSummary(c);
      setEvents(ev);
      if (includeDetails && detail) {
        const updated = await api<Requirement>(`requirements/${detail.id}/`);
        if (generation === requestGeneration.current)
          setDetail((current) =>
            current?.id === detail.id ? updated : current,
          );
      }
      if (includeDetails && docDetail) {
        const updated = await api<Document>(`documents/${docDetail.id}/`);
        if (generation === requestGeneration.current)
          setDocDetail((current) =>
            current?.id === docDetail.id ? updated : current,
          );
      }
    } catch (e) {
      if (generation === requestGeneration.current)
        setError((e as Error).message);
    } finally {
      if (generation === requestGeneration.current) setLoading(false);
    }
  }
  useEffect(() => {
    if (user && cycle) {
      setDetail(null);
      setDocDetail(null);
      void refresh(false);
    }
    return () => {
      requestGeneration.current += 1;
    };
  }, [cycle, user]);
  const selectedCycle = cycles.find((c) => String(c.id) === cycle);
  function navigate(next: string) {
    setPage(next);
    setMobile(false);
    setDetail(null);
    setDocDetail(null);
    setCertification(null);
    setSearch("");
    setAreaFilter("");
    setStatusFilter("");
    setNotice("");
  }
  async function runSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSearchLoading(true);
    setSearchError("");
    try {
      setSearchResults(
        await api<SearchResults>(
          `search/?cycle=${cycle}&q=${encodeURIComponent(searchTerm)}`,
        ),
      );
    } catch (e) {
      setSearchError((e as Error).message);
      setSearchResults(null);
    } finally {
      setSearchLoading(false);
    }
  }
  async function loadReport() {
    if (!cycle) return;
    setReportLoading(true);
    setReportError("");
    try {
      const params = new URLSearchParams({ cycle });
      if (reportArea) params.set("area", reportArea);
      if (reportStatus) params.set("status", reportStatus);
      setReport(await api<ComplianceReport>(`reports/compliance/?${params}`));
    } catch (e) {
      setReportError((e as Error).message);
    } finally {
      setReportLoading(false);
    }
  }
  useEffect(() => {
    if (page === "reports" && cycle) void loadReport();
  }, [page, cycle, reportArea, reportStatus]);
  async function openRequirement(id: number) {
    try {
      setDetail(await api<Requirement>(`requirements/${id}/`));
      setPage("requirements");
      setDocDetail(null);
      setCertification(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function openDocument(id: string) {
    try {
      setDocDetail(await api<Document>(`documents/${id}/`));
      setPage("documents");
      setDetail(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function changed(message: string) {
    setNotice(message);
    await refresh();
  }
  if (initializing)
    return <div className="loading-page">Loading MC Accreditation Hub…</div>;
  if (!user)
    return (
      <Login
        message={sessionMessage}
        onLogin={(u) => {
          clearWorkspace();
          setUser(u);
          navigate("dashboard");
        }}
      />
    );
  const title = nav.find((n) => n[0] === page)?.[1] || "Dashboard";
  const currentSubmissions = submissions.filter((s) => s.current);
  const canManage = areas.some((a) => a.can_manage);
  const filteredRequirements = requirements.filter(
    (r) =>
      (!areaFilter || String(r.area) === areaFilter) &&
      (!statusFilter || r.status === statusFilter) &&
      `${r.title} ${r.code} ${r.description} ${r.responsible}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const filteredDocuments = documents.filter(
    (d) =>
      (!areaFilter || String(d.area) === areaFilter) &&
      `${d.title} ${d.category} ${d.custodian}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const filters = (
    <div className="filters">
      <div className="search-field">
        <Search size={19} />
        <input
          aria-label="Search records"
          placeholder={
            page === "documents"
              ? "Search documents, categories, personnel…"
              : "Search requirements…"
          }
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <select
        aria-label="Filter by area"
        value={areaFilter}
        onChange={(e) => setAreaFilter(e.target.value)}
      >
        <option value="">All Areas</option>
        {areas.map((a) => (
          <option key={a.id} value={a.id}>
            {a.title}
          </option>
        ))}
      </select>
      {page === "requirements" && (
        <select
          aria-label="Filter by status"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          {[
            "complete",
            "ready_for_completion_review",
            "pending",
            "for_compliance",
            "missing",
            "draft",
            "excluded",
          ].map((s) => (
            <option key={s} value={s}>
              {labels[s]}
            </option>
          ))}
        </select>
      )}
    </div>
  );
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobile ? "open" : ""}`}>
        <div className="sidebar-brand">
          <span className="logo">MC</span>
          <div>
            <strong>MC Accreditation Hub</strong>
            <small>Graduate School</small>
          </div>
          <button
            className="mobile-only icon-button"
            aria-label="Close navigation"
            onClick={() => setMobile(false)}
          >
            <X />
          </button>
        </div>
        <div className="nav-label">MAIN</div>
        <nav>
          {nav.map(([key, text, Icon]) => (
            <button
              key={key}
              className={page === key ? "active" : ""}
              onClick={() => navigate(key)}
            >
              <Icon size={19} />
              <span>{text}</span>
              {page === key && <i />}
            </button>
          ))}
        </nav>
        {user.is_staff && (
          <a
            className="admin-link"
            href="/api/admin/"
            target="_blank"
            rel="noreferrer"
          >
            Account Administration ↗
          </a>
        )}
        <div className="sidebar-user">
          <span className="avatar">{initials(user.name)}</span>
          <div>
            <strong>{user.name}</strong>
            <small>{user.assignments[0]?.role || "Administrator"}</small>
          </div>
          <button
            className="icon-button"
            title="Sign out"
            aria-label="Sign out"
            onClick={async () => {
              try {
                await post("auth/logout/", {});
                clearWorkspace();
                setUser(null);
                setCycles([]);
                setCycle("");
                setSessionMessage("");
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <button
            className="mobile-only icon-button"
            aria-label="Open navigation"
            onClick={() => setMobile(true)}
          >
            <Menu />
          </button>
          <div>
            <h2>{title}</h2>
            <p>{subtitles[page]}</p>
          </div>
          <div className="topbar-right">
            <select
              aria-label="Accreditation cycle"
              value={cycle}
              onChange={(e) => {
                setDetail(null);
                setDocDetail(null);
                setCycle(e.target.value);
              }}
            >
              {cycles.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title} {c.status === "closed" ? "(Closed)" : ""}
                </option>
              ))}
            </select>
            <span className="avatar">{initials(user.name)}</span>
          </div>
        </header>
        <main className="content">
          {selectedCycle?.is_demo && (
            <div className="demo-banner">
              <ShieldCheck size={16} />
              Demo cycle · Fictional requirements and evidence. For testing
              only.
            </div>
          )}
          {selectedCycle?.status === "closed" && (
            <div className="demo-banner">
              Archived cycle · Records are read-only.
            </div>
          )}
          <ErrorBox error={error} />
          {notice && (
            <div className="notice" role="status">
              {notice}
              <button
                className="icon-button"
                aria-label="Dismiss message"
                onClick={() => setNotice("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {loading && (
            <div className="loading-line" role="status">
              Updating records…
            </div>
          )}
          {!cycles.length && (
            <div className="panel empty">
              <h2>No assigned accreditation cycles</h2>
              <p>
                An administrator must assign your account to a cycle or area.
              </p>
            </div>
          )}
          {cycle && (page === "dashboard" || page === "compliance") && (
            <>
              <div className="page-heading">
                <div>
                  <h1>
                    {page === "dashboard"
                      ? `Welcome, ${user.name.split(" ")[0]}.`
                      : "Compliance Monitoring"}
                  </h1>
                  <p>
                    {page === "dashboard"
                      ? `Graduate School Accreditation Dashboard — ${date(new Date().toISOString())}`
                      : "Track accreditation compliance across your authorized areas"}
                  </p>
                </div>
                <span className="compliance-label">
                  {percent(summary?.percentage ?? null)} Compliance
                </span>
              </div>
              <div className="stats">
                {[
                  [
                    "📊",
                    percent(summary?.percentage ?? null),
                    "Overall Compliance",
                    "Your authorized areas",
                    "green",
                  ],
                  [
                    "📋",
                    summary?.total ?? 0,
                    "Total Requirements",
                    "Active and applicable",
                    "blue",
                  ],
                  [
                    "✅",
                    summary?.complete ?? 0,
                    "Completed",
                    "Certified by Coordinator",
                    "green",
                  ],
                  [
                    "📋",
                    summary?.ready_for_completion_review ?? 0,
                    "Ready for Completion Review",
                    "Awaiting Coordinator certification",
                    "purple",
                  ],
                  [
                    "🔎",
                    summary?.pending ?? 0,
                    "For Verification",
                    "Awaiting review",
                    "blue",
                  ],
                  [
                    "⚠️",
                    summary?.for_compliance ?? 0,
                    "For Compliance",
                    "Needs attention",
                    "orange",
                  ],
                  [
                    "🔴",
                    summary?.missing ?? 0,
                    "Missing Evidence",
                    "No submitted evidence",
                    "red",
                  ],
                  [
                    "📁",
                    documents.length,
                    "Total Documents",
                    "Accessible in repository",
                    "purple",
                  ],
                ].map(([icon, value, label, hint, color]) => (
                  <div className="stat panel" key={String(label)}>
                    <span className="stat-icon">{icon}</span>
                    <strong className={String(color)}>{value}</strong>
                    <span>{label}</span>
                    <small>{hint}</small>
                  </div>
                ))}
              </div>
              <div className="dashboard-grid">
                <section className="panel readiness">
                  <h3>Requirement Compliance</h3>
                  <div
                    className="donut"
                    style={{
                      background: `conic-gradient(#2861f4 ${(summary?.percentage || 0) * 3.6}deg, #f0f2f6 0deg)`,
                    }}
                  >
                    <div>
                      <strong>{percent(summary?.percentage ?? null)}</strong>
                      <small>
                        {summary?.percentage === null
                          ? "NOT AVAILABLE"
                          : "CERTIFIED"}
                      </small>
                    </div>
                  </div>
                  <p>
                    {summary?.complete || 0} of {summary?.total || 0} applicable
                    requirements complete
                  </p>
                  <small>Calculated from Coordinator-certified requirements.</small>
                </section>
                <section className="panel area-progress">
                  <div className="section-heading">
                    <h3>Accreditation Area Progress</h3>
                    <button className="link" onClick={() => navigate("areas")}>
                      View All Areas <ArrowRight size={16} />
                    </button>
                  </div>
                  {areas.map((a) => (
                    <button
                      className="area-progress-row"
                      key={a.id}
                      onClick={() => {
                        navigate("requirements");
                        setAreaFilter(String(a.id));
                      }}
                    >
                      <span>{a.icon}</span>
                      <div>
                        <div>
                          <span>{a.title}</span>
                          <strong className="green">
                            {percent(a.percentage)}
                          </strong>
                        </div>
                        <Progress value={a.percentage} />
                      </div>
                    </button>
                  ))}
                </section>
              </div>
              <div className="panel formula">
                <h3>How compliance is calculated</h3>
                <p>{summary?.formula}</p>
                <small>
                  Every mandatory evidence item must have an approved, unexpired
                  submission. An assigned Coordinator must then certify the
                  requirement. Draft and non-applicable requirements are
                  excluded.
                </small>
              </div>
            </>
          )}
          {page === "areas" && (
            <>
              <div className="page-heading">
                <div>
                  <h1>Accreditation Areas</h1>
                  <p>
                    {areas.length} areas in {selectedCycle?.title}
                  </p>
                </div>
              </div>
              <div className="area-grid">
                {areas.map((a) => (
                  <button
                    className="panel area-card"
                    key={a.id}
                    onClick={() => {
                      navigate("requirements");
                      setAreaFilter(String(a.id));
                    }}
                  >
                    <div className="area-card-top">
                      <span className="area-icon">{a.icon}</span>
                      <strong className="green">{percent(a.percentage)}</strong>
                    </div>
                    <h3>{a.title}</h3>
                    <Progress value={a.percentage} />
                    <div className="area-counts">
                      <div>
                        <b className="green">{a.complete}</b>
                        <small>Done</small>
                      </div>
                      <div>
                        <b className="blue">{a.pending}</b>
                        <small>Review</small>
                      </div>
                      <div>
                        <b className="red">{a.missing}</b>
                        <small>Missing</small>
                      </div>
                    </div>
                    <small>
                      {a.total} applicable requirements · {a.for_compliance} for
                      compliance
                    </small>
                  </button>
                ))}
              </div>
            </>
          )}
          {page === "requirements" && !detail && (
            <>
              <div className="page-heading">
                <div>
                  <h1>Accreditation Requirements</h1>
                  <p>{filteredRequirements.length} requirements found</p>
                </div>
                {canManage && (
                  <button
                    className="primary"
                    onClick={() => {
                      setEditing(null);
                      setRequirementForm(true);
                    }}
                  >
                    <Plus size={17} />
                    Add Requirement
                  </button>
                )}
              </div>
              {filters}
              <div className="panel table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Requirement</th>
                      <th>Accreditation Area</th>
                      <th>Evidence</th>
                      <th>Responsible</th>
                      <th>Status</th>
                      <th>Deadline</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRequirements.map((r) => (
                      <tr key={r.id}>
                        <td>
                          <strong>{r.title}</strong>
                          <small>
                            {r.code} · {r.description || "No description"}
                          </small>
                        </td>
                        <td>
                          {r.icon} {r.area_title}
                        </td>
                        <td>
                          <span>
                            {r.approved_items}/{r.required_items}
                          </span>
                          <Progress
                            value={
                              r.required_items
                                ? (100 * r.approved_items) / r.required_items
                                : 0
                            }
                          />
                        </td>
                        <td>{r.responsible}</td>
                        <td>
                          <Badge status={r.status} />
                        </td>
                        <td>{date(r.deadline)}</td>
                        <td>
                          <button
                            className="link"
                            onClick={() => openRequirement(r.id)}
                          >
                            View <ArrowRight size={16} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!filteredRequirements.length && (
                  <div className="empty">
                    No requirements match your filters.
                  </div>
                )}
              </div>
            </>
          )}
          {page === "requirements" && detail && (
            <>
              <button className="link back" onClick={() => setDetail(null)}>
                <ArrowLeft size={17} />
                All requirements
              </button>
              <div className="page-heading">
                <div>
                  <h1>{detail.title}</h1>
                  <p>
                    {detail.code} · {detail.area_title}
                  </p>
                </div>
                {detail.can_manage && (
                  <button
                    className="secondary"
                    onClick={() => {
                      setEditing(detail);
                      setRequirementForm(true);
                    }}
                  >
                    Edit Requirement
                  </button>
                )}
              </div>
              <div className="panel requirement-summary">
                <Badge status={detail.status} />
                <p>{detail.description}</p>
                <div className="metadata">
                  <span>
                    Responsible <strong>{detail.responsible}</strong>
                  </span>
                  <span>
                    Deadline <strong>{date(detail.deadline)}</strong>
                  </span>
                  <span>
                    Approved evidence{" "}
                    <strong>
                      {detail.approved_items} / {detail.required_items}
                    </strong>
                  </span>
                </div>
                {!detail.applicable && (
                  <p>Exclusion reason: {detail.exclusion_reason}</p>
                )}
              </div>
              {detail.status === "ready_for_completion_review" && (
                <section className="panel completion-review" aria-live="polite">
                  <div>
                    <h2>Ready for Completion Review</h2>
                    <p>
                      All mandatory evidence is approved and current. An assigned
                      Coordinator must certify this requirement before it counts
                      toward compliance.
                    </p>
                  </div>
                  {detail.can_complete && (
                    <button
                      className="primary"
                      onClick={() =>
                        setCertification({
                          requirement: detail,
                          outcome: "complete",
                        })
                      }
                    >
                      Mark Complete
                    </button>
                  )}
                </section>
              )}
              {detail.status === "complete" && detail.can_reopen && (
                <section className="panel completion-review">
                  <div>
                    <h2>Coordinator certification recorded</h2>
                    <p>
                      This requirement counts toward compliance until an assigned
                      Coordinator reopens it with a rationale.
                    </p>
                  </div>
                  <button
                    className="secondary"
                    onClick={() =>
                      setCertification({
                        requirement: detail,
                        outcome: "reopened",
                      })
                    }
                  >
                    Reopen Requirement
                  </button>
                </section>
              )}
              <section className="panel certification-history">
                <div className="section-heading">
                  <div>
                    <h2>Completion certification history</h2>
                    <p>Coordinator decisions are permanent audit records.</p>
                  </div>
                </div>
                {detail.certifications?.length ? (
                  <div className="certification-list">
                    {detail.certifications.map((entry: Certification) => (
                      <article className="certification-entry" key={entry.id}>
                        <Badge status={entry.outcome} />
                        <div>
                          <strong>
                            {entry.outcome === "complete"
                              ? "Marked complete"
                              : "Reopened requirement"}
                          </strong>
                          <span>
                            {entry.coordinator} · {dateTime(entry.created_at)}
                          </span>
                          <p>{entry.rationale}</p>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : (
                  <div className="empty certification-empty">
                    No Coordinator certification has been recorded yet.
                  </div>
                )}
              </section>
              <div className="section-heading">
                <h2>Evidence checklist</h2>
                <span className="muted">
                  Approvals apply to individual submitted versions
                </span>
              </div>
              {detail.items?.map((item) => (
                <section className="panel evidence-item" key={item.id}>
                  <div className="section-heading">
                    <div>
                      <h3>
                        {item.label}{" "}
                        {item.mandatory && (
                          <small className="muted">Required</small>
                        )}
                      </h3>
                      <p>
                        {item.criteria ||
                          "Review against the requirement description."}
                      </p>
                    </div>
                    <Badge status={item.status} />
                  </div>
                  {item.mappings.map((m) => (
                    <div className="mapping" key={m.id}>
                      <div className="section-heading">
                        <strong>{m.document_title}</strong>
                        {detail.can_upload &&
                          documents.find((d) => d.id === m.document)
                            ?.can_upload && (
                            <button
                              className="link"
                              onClick={() =>
                                setUpload({
                                  doc: documents.find(
                                    (d) => d.id === m.document,
                                  ),
                                  item,
                                  area: detail.area,
                                })
                              }
                            >
                              Upload new version
                            </button>
                          )}
                      </div>
                      {m.submissions.length === 0 ? (
                        <p className="muted">Mapped, not yet submitted.</p>
                      ) : (
                        m.submissions.map((s) => (
                          <div className="submission-line" key={s.id}>
                            <div>
                              <strong>Version {s.version_number}</strong>{" "}
                              <Badge status={s.status} />{" "}
                              {!s.current && <small>Historical</small>}
                              <small>
                                {s.submitted_by} · {date(s.submitted_at)}
                              </small>
                              {s.decision && (
                                <p className="review-comment">
                                  {s.decision.reviewer}:{" "}
                                  {s.decision.comment || "Approved"}{" "}
                                </p>
                              )}
                            </div>
                            <div className="actions">
                              <a
                                className="link"
                                href={`/api/document-versions/${s.version}/download/`}
                              >
                                Download
                              </a>
                              {s.can_review && (
                                <button
                                  className="secondary"
                                  onClick={() => setReview(s)}
                                >
                                  Review
                                </button>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  ))}
                  {detail.can_upload && (
                    <div className="actions">
                      <button
                        className="secondary"
                        onClick={() => setUpload({ item, area: detail.area })}
                      >
                        <Upload size={16} />
                        Upload evidence
                      </button>
                      <button
                        className="link"
                        onClick={() => setMappingItem(item)}
                      >
                        Use existing document
                      </button>
                    </div>
                  )}
                </section>
              ))}
            </>
          )}
          {page === "documents" && !docDetail && (
            <>
              <div className="page-heading">
                <div>
                  <h1>Evidence Repository</h1>
                  <p>
                    Digital repository of accreditation evidence and supporting
                    documents
                  </p>
                </div>
                {areas.some((a) => a.can_upload) && (
                  <button className="primary" onClick={() => setUpload({})}>
                    <Plus size={17} />
                    Upload Document
                  </button>
                )}
              </div>
              {filters}
              <div className="panel table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Document Name</th>
                      <th>Type</th>
                      <th>Area</th>
                      <th>Uploaded By</th>
                      <th>Date</th>
                      <th>Version</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDocuments.map((d) => {
                      const v = d.versions[0];
                      return (
                        <tr key={d.id}>
                          <td>
                            <div className="document-name">
                              <span className="file-icon">
                                {v?.original_name
                                  .split(".")
                                  .pop()
                                  ?.toUpperCase() || "FILE"}
                              </span>
                              <strong>{d.title}</strong>
                            </div>
                          </td>
                          <td>{d.category}</td>
                          <td>{d.area_title}</td>
                          <td>{v?.uploaded_by}</td>
                          <td>{v && date(v.uploaded_at)}</td>
                          <td>v{v?.number}.0</td>
                          <td>
                            <div className="actions">
                              <button
                                className="link"
                                onClick={() => setDocDetail(d)}
                              >
                                View
                              </button>
                              {v && (
                                <a className="link" href={v.download_url}>
                                  Download
                                </a>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
                {!filteredDocuments.length && (
                  <div className="empty">
                    No documents yet. Upload supporting evidence to get started.
                  </div>
                )}
              </div>
            </>
          )}
          {page === "documents" && docDetail && (
            <>
              <button className="link back" onClick={() => setDocDetail(null)}>
                <ArrowLeft size={17} />
                All documents
              </button>
              <div className="page-heading">
                <div>
                  <h1>{docDetail.title}</h1>
                  <p>
                    {docDetail.category} · {docDetail.area_title}
                  </p>
                </div>
                {docDetail.can_upload && (
                  <button
                    className="primary"
                    onClick={() => setUpload({ doc: docDetail })}
                  >
                    <Plus size={17} />
                    New Version
                  </button>
                )}
              </div>
              <section className="panel">
                <h3>Document version history</h3>
                <p className="muted">
                  Uploading a draft does not replace approved evidence. Submit
                  the new version to each requirement that needs it.
                </p>
                {docDetail.versions.map((v) => (
                  <div className="version-row" key={v.id}>
                    <span className="file-icon">v{v.number}</span>
                    <div>
                      <strong>{v.original_name}</strong>
                      <small>
                        {v.uploaded_by} · {date(v.uploaded_at)} ·{" "}
                        {(v.size / 1024).toFixed(1)} KB
                      </small>
                      <small>
                        Valid until:{" "}
                        {v.valid_until ? date(v.valid_until) : "No expiry"}
                      </small>
                      <details>
                        <summary>File checksum</summary>
                        <code>{v.checksum}</code>
                      </details>
                    </div>
                    <a className="link" href={v.download_url}>
                      <Download size={17} />
                      Download
                    </a>
                  </div>
                ))}
              </section>
              <section className="panel">
                <h3>Requirement mappings</h3>
                {docDetail.mappings.length ? (
                  docDetail.mappings.map((m) => (
                    <div className="version-row" key={m.id}>
                      <div>
                        <strong>
                          {m.submissions[0]?.requirement_title ||
                            "Evidence item"}
                        </strong>
                        <small>
                          {m.submissions[0]?.item_label || `Item ${m.item}`}
                        </small>
                      </div>
                      {m.submissions[0] && (
                        <Badge status={m.submissions[0].status} />
                      )}
                    </div>
                  ))
                ) : (
                  <p className="muted">
                    Open a requirement to map and submit this document.
                  </p>
                )}
              </section>
            </>
          )}
          {page === "reviews" && (
            <>
              <div className="page-heading">
                <div>
                  <h1>Evidence Verification</h1>
                  <p>
                    {
                      currentSubmissions.filter((s) => s.status === "pending")
                        .length
                    }{" "}
                    submissions awaiting review
                  </p>
                </div>
              </div>
              <div className="panel table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Evidence</th>
                      <th>Requirement</th>
                      <th>Submitted By</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentSubmissions.map((s) => (
                      <tr key={s.id}>
                        <td>
                          <strong>{s.document_title}</strong>
                          <small>
                            Version {s.version_number} · {s.item_label}
                          </small>
                        </td>
                        <td>{s.requirement_title}</td>
                        <td>
                          {s.submitted_by}
                          <small>{date(s.submitted_at)}</small>
                        </td>
                        <td>
                          <Badge status={s.status} />
                        </td>
                        <td>
                          <div className="actions">
                            {s.can_review ? (
                              <button
                                className="primary"
                                onClick={() => setReview(s)}
                              >
                                Review
                              </button>
                            ) : (
                              <button
                                className="link"
                                onClick={() => openRequirement(s.requirement)}
                              >
                                View details
                              </button>
                            )}
                            <a
                              className="link"
                              href={`/api/document-versions/${s.version}/download/`}
                            >
                              Download
                            </a>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!currentSubmissions.length && (
                  <div className="empty">
                    Submitted evidence will appear here.
                  </div>
                )}
              </div>
            </>
          )}
          {page === "search" && (
            <>
              <div className="page-heading">
                <div>
                  <h1>Search</h1>
                  <p>Search requirement and document metadata in your authorized areas.</p>
                </div>
              </div>
              <form className="panel report-controls" onSubmit={runSearch}>
                <label>
                  Search records
                  <div className="search-field">
                    <Search size={19} />
                    <input
                      aria-label="Search all authorized records"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      placeholder="Requirement, evidence title, area, office..."
                      required
                    />
                  </div>
                </label>
                <button className="primary" disabled={searchLoading}>
                  {searchLoading ? "Searching…" : "Search"}
                </button>
              </form>
              <ErrorBox error={searchError} />
              {searchResults && (
                <div className="search-results">
                  <section className="panel">
                    <h2>Requirements</h2>
                    {searchResults.requirements.length ? searchResults.requirements.map((result) => (
                      <button className="search-result" key={result.id} onClick={() => openRequirement(result.id)}>
                        <div><strong>{result.title}</strong><span>{result.code} · {result.area}</span></div>
                        <Badge status={result.status} />
                      </button>
                    )) : <div className="empty">No matching requirements in your authorized scope.</div>}
                  </section>
                  <section className="panel">
                    <h2>Evidence documents</h2>
                    {searchResults.documents.length ? searchResults.documents.map((result) => (
                      <button className="search-result" key={result.id} onClick={() => {
                        const document = documents.find((entry) => entry.id === result.id);
                        if (document) { setDocDetail(document); setPage("documents"); }
                      }}>
                        <div><strong>{result.title}</strong><span>{result.category} · {result.area}</span></div>
                        <ArrowRight size={18} />
                      </button>
                    )) : <div className="empty">No matching documents in your authorized scope.</div>}
                  </section>
                </div>
              )}
              {!searchResults && !searchLoading && !searchError && (
                <div className="empty">Enter a term to search only records you can access.</div>
              )}
            </>
          )}
          {page === "reports" && (
            <>
              <div className="page-heading report-heading">
                <div>
                  <h1>Compliance Report</h1>
                  <p>Printable readiness report for {selectedCycle?.title || "your selected cycle"}.</p>
                </div>
                <div className="actions no-print">
                  <a className="secondary" href={`/api/reports/compliance/?cycle=${cycle}${reportArea ? `&area=${reportArea}` : ""}${reportStatus ? `&status=${reportStatus}` : ""}&download=csv`}>
                    <Download size={16} /> Export CSV
                  </a>
                  <button className="primary" onClick={() => window.print()}><Printer size={16} /> Print report</button>
                </div>
              </div>
              <section className="panel report-controls no-print">
                <label>Area
                  <select value={reportArea} onChange={(e) => setReportArea(e.target.value)}>
                    <option value="">All authorized areas</option>
                    {areas.map((area) => <option key={area.id} value={area.id}>{area.title}</option>)}
                  </select>
                </label>
                <label>Status
                  <select value={reportStatus} onChange={(e) => setReportStatus(e.target.value)}>
                    <option value="">All statuses</option>
                    {["complete", "ready_for_completion_review", "pending", "for_compliance", "missing", "draft", "excluded"].map((status) => <option key={status} value={status}>{labels[status]}</option>)}
                  </select>
                </label>
              </section>
              <ErrorBox error={reportError} />
              {reportLoading && <div className="loading-line">Updating report…</div>}
              {report && <section className="report-print">
                <div className="report-summary">
                  <div className="panel"><strong>{percent(report.percentage)}</strong><span>Compliance</span></div>
                  <div className="panel"><strong>{report.complete}</strong><span>Completed</span></div>
                  <div className="panel"><strong>{report.total}</strong><span>Applicable requirements</span></div>
                  <div className="panel"><strong>{report.ready_for_completion_review}</strong><span>Ready for review</span></div>
                </div>
                <section className="panel table-wrap">
                  <div className="report-meta"><span>{report.scope}</span><span>Calculated {dateTime(report.calculated_at)}</span></div>
                  <table>
                    <thead><tr><th>Area</th><th>Code</th><th>Requirement</th><th>Responsible</th><th>Evidence</th><th>Status</th><th>Deadline</th></tr></thead>
                    <tbody>{report.rows.map((row) => <tr key={row.id}><td>{row.area}</td><td>{row.code}</td><td><strong>{row.title}</strong></td><td>{row.responsible}</td><td>{row.approved_items}/{row.required_items}</td><td><Badge status={row.status} /></td><td>{date(row.deadline)}</td></tr>)}</tbody>
                  </table>
                  {!report.rows.length && <div className="empty">No requirements match this report filter.</div>}
                </section>
                <p className="report-formula">{report.formula}. Internal preparation measure only.</p>
              </section>}
            </>
          )}
          {page === "audit" && (
            <>
              <div className="page-heading">
                <div>
                  <h1>Audit Trail</h1>
                  <p>Latest 200 activities in areas you can monitor</p>
                </div>
              </div>
              <div className="panel table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Action</th>
                      <th>Record</th>
                      <th>Date & Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((e) => (
                      <tr key={e.id}>
                        <td>{e.actor}</td>
                        <td>
                          <span className="badge pending">
                            {e.action.replaceAll("_", " ")}
                          </span>
                        </td>
                        <td>{e.record}</td>
                        <td>
                          {new Date(e.created_at).toLocaleString("en-PH")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!events.length && (
                  <div className="empty">
                    No audit events available for your role and scope.
                  </div>
                )}
              </div>
            </>
          )}
          <footer className="content-footer">
            MC Accreditation Hub · Graduate School of Mabini Colleges, Inc.
          </footer>
        </main>
      </div>
      {requirementForm && (
        <RequirementForm
          areas={areas.filter((a) => a.can_manage)}
          editing={editing}
          close={() => setRequirementForm(false)}
          saved={async () => {
            setRequirementForm(false);
            await changed("Requirement saved.");
          }}
        />
      )}
      {upload && (
        <UploadForm
          context={upload}
          areas={areas.filter((a) => a.can_upload)}
          close={() => setUpload(null)}
          saved={async (message) => {
            setUpload(null);
            await changed(message);
          }}
        />
      )}
      {mappingItem && (
        <MappingForm
          item={mappingItem}
          documents={documents}
          close={() => setMappingItem(null)}
          saved={async () => {
            setMappingItem(null);
            await changed("Evidence submitted for verification.");
          }}
        />
      )}
      {review && (
        <ReviewForm
          submission={review}
          close={() => setReview(null)}
          saved={async () => {
            setReview(null);
            await changed("Review recorded. Compliance has been recalculated.");
          }}
        />
      )}
      {certification && (
        <CertificationForm
          requirement={certification.requirement}
          outcome={certification.outcome}
          close={() => setCertification(null)}
          saved={async () => {
            setCertification(null);
            await changed(
              certification.outcome === "complete"
                ? "Requirement marked complete. Compliance has been recalculated."
                : "Requirement reopened. Compliance has been recalculated.",
            );
          }}
        />
      )}
    </div>
  );
}

function RequirementForm({
  areas,
  editing,
  close,
  saved,
}: {
  areas: Area[];
  editing: Requirement | null;
  close: () => void;
  saved: () => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [applicable, setApplicable] = useState(editing?.applicable ?? true);
  const [items, setItems] = useState([{ label: "", criteria: "" }]);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    const data = {
      area: Number(f.get("area")),
      code: f.get("code"),
      title: f.get("title"),
      description: f.get("description"),
      responsible: f.get("responsible"),
      deadline: f.get("deadline") || null,
      active: f.get("active") === "on",
      applicable,
      exclusion_reason: applicable ? "" : f.get("exclusion_reason"),
      ...(!editing
        ? { items: items.map((i) => ({ ...i, mandatory: true })) }
        : {}),
    };
    try {
      await api(editing ? `requirements/${editing.id}/` : "requirements/", {
        method: editing ? "PATCH" : "POST",
        body: JSON.stringify(data),
      });
      await saved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={editing ? "Edit Requirement" : "Add Requirement"}
      close={close}
    >
      <form onSubmit={submit}>
        <ErrorBox error={error} />
        <div className="form-grid">
          <label>
            Accreditation area
            <select
              name="area"
              defaultValue={editing?.area || areas[0]?.id}
              disabled={!!editing}
            >
              {areas.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.title}
                </option>
              ))}
            </select>
            {editing && (
              <input type="hidden" name="area" value={editing.area} />
            )}
          </label>
          <label>
            Requirement code
            <input
              name="code"
              required
              maxLength={40}
              defaultValue={editing?.code}
              placeholder="FAC-001"
            />
          </label>
        </div>
        <label>
          Requirement title
          <input
            name="title"
            required
            maxLength={180}
            defaultValue={editing?.title}
          />
        </label>
        <label>
          Description / acceptance criteria
          <textarea
            name="description"
            rows={3}
            defaultValue={editing?.description}
          />
        </label>
        <div className="form-grid">
          <label>
            Responsible office / person
            <input
              name="responsible"
              required
              maxLength={180}
              defaultValue={editing?.responsible}
            />
          </label>
          <label>
            Deadline
            <input
              type="date"
              name="deadline"
              defaultValue={editing?.deadline || ""}
            />
          </label>
        </div>
        <label className="check">
          <input
            type="checkbox"
            name="active"
            defaultChecked={editing?.active ?? true}
          />
          Active requirement
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={applicable}
            onChange={(e) => setApplicable(e.target.checked)}
          />
          Applicable to this cycle
        </label>
        {!applicable && (
          <label>
            Exclusion reason
            <textarea
              name="exclusion_reason"
              required
              defaultValue={editing?.exclusion_reason}
            />
          </label>
        )}
        {!editing && (
          <fieldset>
            <legend>Mandatory evidence checklist</legend>
            {items.map((item, i) => (
              <div className="checklist-edit" key={i}>
                <label>
                  Evidence item {i + 1}
                  <input
                    required
                    maxLength={180}
                    value={item.label}
                    onChange={(e) =>
                      setItems(
                        items.map((x, n) =>
                          n === i ? { ...x, label: e.target.value } : x,
                        ),
                      )
                    }
                    placeholder="e.g. Faculty development plan"
                  />
                </label>
                <label>
                  Acceptance criteria
                  <input
                    value={item.criteria}
                    onChange={(e) =>
                      setItems(
                        items.map((x, n) =>
                          n === i ? { ...x, criteria: e.target.value } : x,
                        ),
                      )
                    }
                    placeholder="What must this evidence demonstrate?"
                  />
                </label>
                {items.length > 1 && (
                  <button
                    className="link"
                    type="button"
                    onClick={() => setItems(items.filter((_, n) => n !== i))}
                  >
                    Remove item
                  </button>
                )}
              </div>
            ))}
            <button
              className="link"
              type="button"
              onClick={() => setItems([...items, { label: "", criteria: "" }])}
            >
              <Plus size={16} />
              Add evidence item
            </button>
          </fieldset>
        )}
        <div className="form-actions">
          <button className="secondary" type="button" onClick={close}>
            Cancel
          </button>
          <button className="primary" disabled={busy}>
            {busy ? "Saving…" : "Save Requirement"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function UploadForm({
  context,
  areas,
  close,
  saved,
}: {
  context: { doc?: Document; item?: Item; area?: number };
  areas: Area[];
  close: () => void;
  saved: (message: string) => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [uploaded, setUploaded] = useState<Document | null>(null);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    if (!f.get("valid_until")) f.delete("valid_until");
    try {
      const doc =
        uploaded ||
        (await api<Document>(
          context.doc ? `documents/${context.doc.id}/versions/` : "documents/",
          { method: "POST", body: f },
        ));
      setUploaded(doc);
      if (context.item) {
        const m = await post<{ id: number }>("evidence-mappings/", {
          item: context.item.id,
          document: doc.id,
        });
        await post("submissions/", {
          mapping: m.id,
          version: doc.versions[0].id,
        });
      }
      await saved(
        context.item
          ? "Evidence uploaded and submitted for verification."
          : "Draft version uploaded. Open a requirement to map and submit it.",
      );
    } catch (e) {
      setError(
        (uploaded ? "The file is saved. Retry submission: " : "") +
          (e as Error).message,
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={
        context.doc ? `New Version: ${context.doc.title}` : "Upload Evidence"
      }
      close={close}
    >
      <form onSubmit={submit}>
        <ErrorBox error={error} />
        {context.item && (
          <p className="muted">
            Submit evidence for: <strong>{context.item.label}</strong>
          </p>
        )}
        {!context.doc && (
          <>
            <label>
              Document title
              <input
                name="title"
                required
                maxLength={180}
                disabled={!!uploaded}
              />
            </label>
            <div className="form-grid">
              <label>
                Owning area
                <select
                  name="area"
                  defaultValue={context.area || areas[0]?.id}
                  disabled={!!uploaded}
                >
                  {areas.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Document type
                <select name="category" disabled={!!uploaded}>
                  {[
                    "Supporting Document",
                    "Policy / Plan",
                    "Report",
                    "Inventory",
                    "Minutes",
                    "Certificate",
                  ].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
            </div>
          </>
        )}
        <label className="upload-zone">
          <Upload size={28} />
          <strong>Choose a document</strong>
          <span>PDF, DOCX, XLSX, PNG or JPEG · Up to 25 MB</span>
          <input
            name="file"
            type="file"
            accept=".pdf,.docx,.xlsx,.png,.jpg,.jpeg"
            required={!uploaded}
            disabled={!!uploaded}
          />
        </label>
        <label>
          Valid until (optional)
          <input name="valid_until" type="date" disabled={!!uploaded} />
        </label>
        <p className="muted">
          Every upload creates an immutable version. Approvals never carry over
          automatically.
        </p>
        <div className="form-actions">
          <button className="secondary" type="button" onClick={close}>
            Cancel
          </button>
          <button className="primary" disabled={busy}>
            {busy
              ? "Saving…"
              : uploaded
                ? "Retry submission"
                : context.item
                  ? "Upload & Submit"
                  : "Upload Draft"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function MappingForm({
  item,
  documents,
  close,
  saved,
}: {
  item: Item;
  documents: Document[];
  close: () => void;
  saved: () => Promise<void>;
}) {
  const eligible = documents.filter((d) => d.can_upload),
    [docId, setDocId] = useState(eligible[0]?.id || ""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const doc = eligible.find((d) => d.id === docId);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      const m = await post<{ id: number }>("evidence-mappings/", {
        item: item.id,
        document: docId,
      });
      await post("submissions/", {
        mapping: m.id,
        version: Number(f.get("version")),
      });
      await saved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Use Existing Document" close={close}>
      <form onSubmit={submit}>
        <ErrorBox error={error} />
        <p>
          Submit a specific version for <strong>{item.label}</strong>.
        </p>
        <label>
          Document
          <select
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
            required
          >
            {eligible.map((d) => (
              <option key={d.id} value={d.id}>
                {d.title}
              </option>
            ))}
          </select>
        </label>
        <label>
          Version
          <select name="version" key={docId} required>
            {doc?.versions.map((v) => (
              <option key={v.id} value={v.id}>
                v{v.number} — {v.original_name}
              </option>
            ))}
          </select>
        </label>
        {!eligible.length && (
          <p className="muted">Upload a document in an assigned area first.</p>
        )}
        <div className="form-actions">
          <button className="secondary" type="button" onClick={close}>
            Cancel
          </button>
          <button className="primary" disabled={busy || !docId}>
            {busy ? "Submitting…" : "Submit for Verification"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ReviewForm({
  submission,
  close,
  saved,
}: {
  submission: Submission;
  close: () => void;
  saved: () => Promise<void>;
}) {
  const [outcome, setOutcome] = useState("approved"),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      await post("review-decisions/", {
        submission: submission.id,
        outcome,
        comment: f.get("comment"),
      });
      await saved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal title="Review Evidence" close={close}>
      <form onSubmit={submit}>
        <ErrorBox error={error} />
        <div className="review-context">
          <h3>{submission.document_title}</h3>
          <p>
            Version {submission.version_number} · {submission.item_label}
          </p>
          <small>{submission.requirement_title}</small>
          <a
            className="link"
            href={`/api/document-versions/${submission.version}/download/`}
          >
            <Download size={16} />
            Download this version
          </a>
        </div>
        <label>
          Decision
          <select value={outcome} onChange={(e) => setOutcome(e.target.value)}>
            <option value="approved">Approve</option>
            <option value="revision_requested">Request revisions</option>
            <option value="rejected">Reject</option>
          </select>
        </label>
        <label>
          Review comments {outcome !== "approved" ? "(required)" : "(optional)"}
          <textarea
            name="comment"
            required={outcome !== "approved"}
            rows={4}
            placeholder="Explain your decision or specify the changes needed."
          />
        </label>
        <p className="muted">
          This decision applies only to version {submission.version_number} for
          this evidence item and will be preserved in the audit trail.
        </p>
        <div className="form-actions">
          <button type="button" className="secondary" onClick={close}>
            Cancel
          </button>
          <button className="primary" disabled={busy}>
            {busy ? "Recording…" : "Record Decision"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function CertificationForm({
  requirement,
  outcome,
  close,
  saved,
}: {
  requirement: Requirement;
  outcome: "complete" | "reopened";
  close: () => void;
  saved: () => Promise<void>;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const completing = outcome === "complete";
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const f = new FormData(e.currentTarget);
    try {
      await post(`requirements/${requirement.id}/certifications/`, {
        outcome,
        rationale: f.get("rationale"),
      });
      await saved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={completing ? "Mark Requirement Complete" : "Reopen Requirement"}
      close={close}
    >
      <form onSubmit={submit}>
        <ErrorBox error={error} />
        <div className="review-context">
          <h3>{requirement.title}</h3>
          <p>
            {completing
              ? "This will count the requirement toward compliance."
              : "This will remove the requirement from completed compliance."}
          </p>
        </div>
        <label>
          Rationale
          <textarea
            name="rationale"
            required
            minLength={1}
            rows={4}
            placeholder={
              completing
                ? "State why this requirement is ready to be completed."
                : "State why this requirement must be reopened."
            }
          />
        </label>
        <p className="muted">
          Your decision, rationale, and date will be retained in the
          certification and audit history.
        </p>
        <div className="form-actions">
          <button type="button" className="secondary" onClick={close}>
            Cancel
          </button>
          <button className="primary" disabled={busy}>
            {busy
              ? "Saving…"
              : completing
                ? "Mark Complete"
                : "Reopen Requirement"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
