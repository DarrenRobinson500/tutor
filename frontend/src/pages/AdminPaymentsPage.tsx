import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface BankDetails {
  bank_bsb: string;
  bank_account: string;
  bank_name: string;
}

function BankDetailsSection() {
  const [details, setDetails] = useState<BankDetails | null>(null);
  const [editing, setEditing] = useState(false);
  const [bsb, setBsb] = useState("");
  const [account, setAccount] = useState("");
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    apiFetch("/api/admin-jobs/bank_details/")
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d) {
          setDetails(d);
          setBsb(d.bank_bsb ?? "");
          setAccount(d.bank_account ?? "");
          setName(d.bank_name ?? "");
        }
      })
      .catch(() => {});
  }, []);

  async function handleSave() {
    if (!bsb.trim() || !account.trim()) {
      setError("BSB and account number are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await apiFetch("/api/admin-jobs/bank_details/", {
        method: "POST",
        body: JSON.stringify({ bank_bsb: bsb.trim(), bank_account: account.trim(), bank_name: name.trim() }),
      });
      if (!res.ok) {
        const d = await res.json();
        setError(d.error ?? "Failed to save.");
      } else {
        setDetails({ bank_bsb: bsb.trim(), bank_account: account.trim(), bank_name: name.trim() });
        setEditing(false);
      }
    } catch {
      setError("Network error.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mb-4 p-3 rounded" style={{ background: "#f8f9fa", border: "1px solid #dee2e6" }}>
      <div className="d-flex align-items-center justify-content-between mb-2">
        <h6 className="mb-0" style={{ fontSize: "0.9rem", fontWeight: 600 }}>Bank transfer details</h6>
        {!editing && (
          <button className="btn btn-sm btn-outline-secondary" style={{ fontSize: "0.8rem" }} onClick={() => setEditing(true)}>
            Edit
          </button>
        )}
      </div>

      {!editing && details && (details.bank_bsb || details.bank_account) && (
        <div className="d-flex gap-4" style={{ fontSize: "0.85rem" }}>
          {details.bank_name && <span><span className="text-muted">Name: </span>{details.bank_name}</span>}
          {details.bank_bsb && <span><span className="text-muted">BSB: </span><code>{details.bank_bsb}</code></span>}
          {details.bank_account && <span><span className="text-muted">Account: </span><code>{details.bank_account}</code></span>}
        </div>
      )}

      {!editing && (!details || (!details.bank_bsb && !details.bank_account)) && (
        <p className="text-muted mb-0" style={{ fontSize: "0.85rem" }}>No bank details set.</p>
      )}

      {editing && (
        <div className="d-flex flex-column gap-2" style={{ maxWidth: 360 }}>
          <div>
            <label className="form-label mb-1" style={{ fontSize: "0.82rem", fontWeight: 600 }}>Account name</label>
            <input className="form-control form-control-sm" placeholder="e.g. SubjectMatter Pty Ltd" value={name} onChange={e => setName(e.target.value)} />
          </div>
          <div>
            <label className="form-label mb-1" style={{ fontSize: "0.82rem", fontWeight: 600 }}>BSB <span className="text-danger">*</span></label>
            <input className="form-control form-control-sm" placeholder="e.g. 062-000" value={bsb} onChange={e => setBsb(e.target.value)} />
          </div>
          <div>
            <label className="form-label mb-1" style={{ fontSize: "0.82rem", fontWeight: 600 }}>Account number <span className="text-danger">*</span></label>
            <input className="form-control form-control-sm" placeholder="e.g. 1234 5678" value={account} onChange={e => setAccount(e.target.value)} />
          </div>
          {error && <p className="text-danger mb-0" style={{ fontSize: "0.82rem" }}>{error}</p>}
          <div className="d-flex gap-2">
            <button className="btn btn-sm btn-success" onClick={handleSave} disabled={saving}>{saving ? "Saving…" : "Save"}</button>
            <button className="btn btn-sm btn-outline-secondary" onClick={() => { setEditing(false); setError(""); }} disabled={saving}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

interface PaymentRow {
  id: number;
  date_tuition: string | null;
  student_name: string;
  tutor_name: string;
  amount_paid: string;
  amount_tutor: string;
  amount_platform: string;
  amount_distributor: string;
  focus_area: string;
}

interface MonthBlock {
  label?: string;
  payments: PaymentRow[];
  total_paid: string;
  total_tutor: string;
  total_platform: string;
  total_distributor: string;
}

interface PaymentsData {
  current_month: MonthBlock;
  last_month: MonthBlock;
  older: MonthBlock;
}

function fmt(date: string | null) {
  if (!date) return "—";
  return new Date(date).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" });
}

function currency(val: string) {
  return `$${parseFloat(val).toFixed(2)}`;
}

function SummaryBar({ block }: { block: MonthBlock }) {
  return (
    <div className="d-flex gap-4 mb-3 p-3 rounded" style={{ background: "#f8f9fa", fontSize: 13 }}>
      <div>
        <div className="text-muted">Received</div>
        <div className="fw-semibold text-success">{currency(block.total_paid)}</div>
      </div>
      <div>
        <div className="text-muted">To Tutors</div>
        <div className="fw-semibold">{currency(block.total_tutor)}</div>
      </div>
      <div>
        <div className="text-muted">Platform</div>
        <div className="fw-semibold">{currency(block.total_platform)}</div>
      </div>
      <div>
        <div className="text-muted">Distributors</div>
        <div className="fw-semibold">{currency(block.total_distributor)}</div>
      </div>
    </div>
  );
}

function PaymentTable({ payments }: { payments: PaymentRow[] }) {
  if (payments.length === 0) {
    return <p className="text-muted" style={{ fontSize: 13 }}>No payments this period.</p>;
  }
  return (
    <table className="table table-sm table-hover" style={{ fontSize: 13 }}>
      <thead className="table-light">
        <tr>
          <th>Date</th>
          <th>Student</th>
          <th>Tutor</th>
          <th>Focus Area</th>
          <th className="text-end">Received</th>
          <th className="text-end">Tutor</th>
          <th className="text-end">Platform</th>
          <th className="text-end">Distributor</th>
        </tr>
      </thead>
      <tbody>
        {payments.map(p => (
          <tr key={p.id}>
            <td>{fmt(p.date_tuition)}</td>
            <td>{p.student_name}</td>
            <td>{p.tutor_name}</td>
            <td className="text-muted">{p.focus_area || "—"}</td>
            <td className="text-end fw-semibold">{currency(p.amount_paid)}</td>
            <td className="text-end">{currency(p.amount_tutor)}</td>
            <td className="text-end">{currency(p.amount_platform)}</td>
            <td className="text-end">{currency(p.amount_distributor)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function MonthSection({ title, block }: { title: string; block: MonthBlock }) {
  return (
    <div className="mb-4">
      <h5 className="mb-2">{title}{block.label ? ` — ${block.label}` : ""}</h5>
      <SummaryBar block={block} />
      <PaymentTable payments={block.payments} />
    </div>
  );
}

export function AdminPaymentsPage() {
  const [data, setData] = useState<PaymentsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showOlder, setShowOlder] = useState(false);

  useEffect(() => {
    apiFetch("/api/admin-jobs/payments/")
      .then(r => r.json())
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Layout>
      <div className="container mt-4" style={{ maxWidth: 1000 }}>
        <h3 className="mb-4">Payments</h3>
        <BankDetailsSection />

        {loading && <p className="text-muted">Loading…</p>}

        {!loading && !data && (
          <p className="text-danger">Failed to load payments.</p>
        )}

        {data && (
          <>
            <MonthSection title="This Month" block={data.current_month} />
            <MonthSection title="Last Month" block={data.last_month} />

            {data.older.payments.length > 0 && (
              <div className="mb-4">
                <button
                  className="btn btn-sm btn-outline-secondary mb-2"
                  onClick={() => setShowOlder(v => !v)}
                >
                  {showOlder ? "Hide older payments" : `Show older payments (${data.older.payments.length})`}
                </button>
                {showOlder && (
                  <MonthSection title="Older" block={data.older} />
                )}
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
