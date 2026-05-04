import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface StudentRow {
  id: number;
  name: string;
  username: string;
  email: string;
  year_level: string;
  score_pct: number;
}

interface ClassDetail {
  id: number;
  name: string;
  year_level: string;
  code: string;
  student_count: number;
  students: StudentRow[];
}

interface ImportedStudent {
  id?: number;
  name?: string;
  username?: string;
  email?: string;
  pin?: string;
  new_account?: boolean;
  error?: string;
}

export function TeacherClassPage() {
  const { teacherId, classId } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<ClassDetail | null>(null);
  const [loading, setLoading] = useState(true);

  // Import panel
  const [showImport, setShowImport] = useState(false);
  const [importText, setImportText] = useState("");
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const [importResults, setImportResults] = useState<ImportedStudent[]>([]);

  function load() {
    apiFetch(`/api/teachers/${teacherId}/class_detail/?class_id=${classId}`)
      .then((r) => r.json())
      .then((data) => setDetail(data))
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, [teacherId, classId]);

  function parseImportText(raw: string): { first_name: string; last_name: string; email: string }[] {
    // Accepts (one student per line):
    //   First Last  email@example.com     — space-delimited (Excel paste)
    //   First Last, email@example.com     — comma after name
    //   First, Last, email@example.com    — three comma-separated columns
    //   First\tLast\temail@example.com    — tab-separated (Excel copy)
    return raw
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
      .map((line) => {
        // Normalise: split on tab or comma first
        const parts = line.split(/,|\t/).map((p) => p.trim());
        if (parts.length >= 3) {
          return { first_name: parts[0], last_name: parts[1], email: parts[2] };
        }
        if (parts.length === 2) {
          const maybeEmail = parts[1].includes("@");
          if (maybeEmail) {
            // "First Last, email" or "FirstLast, email"
            const nameParts = parts[0].split(" ");
            return {
              first_name: nameParts[0] ?? "",
              last_name: nameParts.slice(1).join(" ") || parts[0],
              email: parts[1],
            };
          }
          // "First, Last" with no email — keep for validation error on submit
          return { first_name: parts[0], last_name: parts[1], email: "" };
        }
        // Single token — try to split "First Last email@x.com" on spaces
        const words = parts[0].split(/\s+/);
        const emailIdx = words.findIndex((w) => w.includes("@"));
        if (emailIdx >= 0) {
          const email = words[emailIdx];
          const nameWords = words.filter((_, i) => i !== emailIdx);
          return {
            first_name: nameWords[0] ?? "",
            last_name: nameWords.slice(1).join(" ") || "?",
            email,
          };
        }
        return { first_name: words[0] ?? "", last_name: words.slice(1).join(" ") || "?", email: "" };
      });
  }

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();
    setImportError("");
    setImportResults([]);
    const students = parseImportText(importText);
    if (!students.length) { setImportError("No valid rows found."); return; }
    const missingEmail = students.filter((s) => !s.email);
    if (missingEmail.length) {
      setImportError(`Email required for every student. Missing for: ${missingEmail.map((s) => `${s.first_name} ${s.last_name}`).join(", ")}`);
      return;
    }

    setImporting(true);
    try {
      const res = await apiFetch(`/api/teachers/${teacherId}/import_students/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ class_id: Number(classId), students }),
      });
      const data = await res.json();
      if (!res.ok) { setImportError(data.error || "Import failed."); return; }
      setImportResults(data.imported ?? []);
      setImportText("");
      load();
    } finally {
      setImporting(false);
    }
  }

  if (loading) return <Layout><div className="container mt-4">Loading…</div></Layout>;
  if (!detail) return <Layout><div className="container mt-4">Class not found.</div></Layout>;

  const newAccounts = importResults.filter((r) => r.new_account && r.pin);
  const hasErrors = importResults.some((r) => r.error);

  return (
    <Layout>
      <div className="container mt-4">

        {/* ── Header ───────────────────────────────── */}
        <div className="d-flex align-items-center gap-2 mb-1">
          <Link to={`/teachers/${teacherId}`} className="btn btn-sm btn-outline-secondary">
            ← Back
          </Link>
          <h2 className="mb-0">{detail.name}</h2>
          <span className="badge bg-secondary">Year {detail.year_level}</span>
        </div>
        <p className="text-muted mb-3" style={{ fontSize: 13 }}>
          Join code: <strong>{detail.code}</strong> · {detail.student_count} student{detail.student_count !== 1 ? "s" : ""}
        </p>

        <div className="d-flex gap-2 mb-4">
          <button
            className="btn btn-primary"
            onClick={() => { setShowImport((v) => !v); setImportResults([]); }}
          >
            {showImport ? "Cancel" : "+ Import Students"}
          </button>
        </div>

        {/* ── Import panel ─────────────────────────── */}
        {showImport && (
          <div className="card mb-4 border-primary">
            <div className="card-body">
              <h5 className="card-title">Import Students</h5>
              <p className="text-muted" style={{ fontSize: 13 }}>
                Paste one student per line — email is required for every student.
                Accepted formats:
                <br />
                <code>First Last email@example.com</code> — space-delimited (Excel paste)<br />
                <code>First Last, email@example.com</code> — comma after name<br />
                <code>First, Last, email@example.com</code> — three comma-separated columns<br />
                A 4-character password will be generated and emailed to each new student.
              </p>
              {importError && <div className="alert alert-danger">{importError}</div>}
              <form onSubmit={handleImport}>
                <textarea
                  className="form-control font-monospace mb-3"
                  rows={8}
                  placeholder={"Aisha Khan aisha.khan@school.nsw.edu.au\nBen Thompson ben.thompson@school.nsw.edu.au\nChloe Morris, chloe.morris@school.nsw.edu.au"}
                  value={importText}
                  onChange={(e) => setImportText(e.target.value)}
                />
                <button type="submit" className="btn btn-primary" disabled={importing}>
                  {importing ? "Importing…" : `Import ${parseImportText(importText).length || 0} student${parseImportText(importText).length !== 1 ? "s" : ""}`}
                </button>
              </form>

              {/* Results — show PIN credentials for new no-email accounts */}
              {importResults.length > 0 && (
                <div className="mt-4">
                  <div className="alert alert-success">
                    {importResults.filter((r) => !r.error).length} student{importResults.filter((r) => !r.error).length !== 1 ? "s" : ""} imported successfully.
                    {hasErrors && <span className="text-danger ms-2">Some rows had errors.</span>}
                  </div>

                  {newAccounts.length > 0 && (
                    <div>
                      <p className="fw-semibold mb-2">
                        New student accounts — passwords have been emailed. Keep a copy below:
                      </p>
                      <div className="table-responsive">
                        <table className="table table-sm table-bordered">
                          <thead className="table-light">
                            <tr>
                              <th>Name</th>
                              <th>Email</th>
                              <th>Password</th>
                            </tr>
                          </thead>
                          <tbody>
                            {newAccounts.map((r, i) => (
                              <tr key={i}>
                                <td>{r.name}</td>
                                <td><code>{r.email}</code></td>
                                <td><strong>{r.pin}</strong></td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="d-flex gap-2">
                        <button
                          className="btn btn-sm btn-outline-secondary"
                          onClick={() => window.print()}
                        >
                          🖨 Print credentials
                        </button>
                        <EmailCredentialsButton
                          teacherId={teacherId!}
                          classId={classId!}
                          credentials={newAccounts.map((r) => ({ id: r.id!, email: r.email!, pin: r.pin! }))}
                        />
                      </div>
                    </div>
                  )}

                  {hasErrors && (
                    <div className="mt-3">
                      <p className="text-danger fw-semibold">Rows with errors:</p>
                      <ul>
                        {importResults.filter((r) => r.error).map((r, i) => (
                          <li key={i} className="text-danger">{r.error}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── Student list ─────────────────────────── */}
        {detail.students.length === 0 ? (
          <div className="text-center py-5 text-muted">
            <p style={{ fontSize: "2.5rem" }}>👨‍🎓</p>
            <h5>No students yet</h5>
            <p>Use the Import Students button to add your class.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="table table-hover align-middle">
              <thead className="table-light">
                <tr>
                  <th>Name</th>
                  <th>Username / Email</th>
                  <th>Year</th>
                  <th>Overall Score</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {detail.students.map((s) => (
                  <tr key={s.id}>
                    <td className="fw-semibold">{s.name}</td>
                    <td className="text-muted" style={{ fontSize: 13 }}>{s.username}</td>
                    <td>Year {s.year_level}</td>
                    <td>
                      <div className="d-flex align-items-center gap-2">
                        <div
                          className="progress flex-grow-1"
                          style={{ height: 8 }}
                          title={`${s.score_pct}%`}
                        >
                          <div
                            className="progress-bar"
                            style={{
                              width: `${Math.min(s.score_pct, 100)}%`,
                              background: s.score_pct >= 60 ? "#43a047" : s.score_pct >= 30 ? "#FF8C42" : "#e53935",
                            }}
                          />
                        </div>
                        <span style={{ fontSize: 12, width: 38, flexShrink: 0 }}>
                          {s.score_pct}%
                        </span>
                      </div>
                    </td>
                    <td>
                      <Link
                        to={`/students/${s.id}`}
                        className="btn btn-sm btn-outline-primary"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}

function EmailCredentialsButton({
  teacherId,
  classId,
  credentials,
}: {
  teacherId: string;
  classId: string;
  credentials: { id: number; email: string; pin: string }[];
}) {
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  async function handleEmail() {
    setSending(true);
    try {
      await apiFetch(`/api/teachers/${teacherId}/email_credentials/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ class_id: Number(classId), credentials }),
      });
      setSent(true);
    } finally {
      setSending(false);
    }
  }

  if (sent) return <span className="text-success" style={{ fontSize: 13 }}>✓ Emails sent</span>;

  return (
    <button
      className="btn btn-sm btn-outline-primary"
      onClick={handleEmail}
      disabled={sending}
    >
      {sending ? "Sending…" : "✉ Email credentials"}
    </button>
  );
}
