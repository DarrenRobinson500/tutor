import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface Setting {
  key: string;
  value: string;
}

const SYSTEM_KEYS: { key: string; label: string; description: string }[] = [
  { key: "platform_fee",               label: "Platform Fee ($)",            description: "Added to the tutor's rate on the Available Tutors page and at checkout." },
  { key: "cancellation_notice_hours",  label: "Cancellation Notice (hours)", description: "Minimum hours before a session that a student can cancel or reschedule." },
  { key: "booking_notice_hours",       label: "Booking Notice (hours)",      description: "Minimum hours ahead a parent or student must book a session." },
];

const DEV_USER_ROLES = [
  { role: "Admin",   emailKey: "dev_admin_email",   passwordKey: "dev_admin_password" },
  { role: "Parent",  emailKey: "dev_parent_email",   passwordKey: "dev_parent_password" },
  { role: "Student", emailKey: "dev_student_email",  passwordKey: "dev_student_password" },
  { role: "Tutor",   emailKey: "dev_tutor_email",    passwordKey: "dev_tutor_password" },
];

export function VariablesPage() {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [drafts, setDrafts]     = useState<Record<string, string>>({});
  const [saved, setSaved]       = useState<Record<string, boolean>>({});
  const [loading, setLoading]   = useState(true);

  useEffect(() => {
    apiFetch("/api/admin/variables/")
      .then(r => r.json())
      .then((data: Setting[]) => {
        const map: Record<string, string> = {};
        data.forEach(s => { map[s.key] = s.value; });
        setSettings(map);
        setDrafts(map);
      })
      .finally(() => setLoading(false));
  }, []);

  function setDraft(key: string, value: string) {
    setDrafts(prev => ({ ...prev, [key]: value }));
    setSaved(prev => ({ ...prev, [key]: false }));
  }

  async function save(key: string) {
    await apiFetch("/api/admin/variables/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value: drafts[key] }),
    });
    setSettings(prev => ({ ...prev, [key]: drafts[key] }));
    setSaved(prev => ({ ...prev, [key]: true }));
    setTimeout(() => setSaved(prev => ({ ...prev, [key]: false })), 2000);
  }

  function renderRow(key: string, label: string, description: string, type: "text" | "number" = "text") {
    const dirty = drafts[key] !== settings[key];
    return (
      <tr key={key}>
        <td style={{ width: 220, fontWeight: 500 }}>{label}</td>
        <td style={{ width: 200 }}>
          <input
            type={type}
            className="form-control form-control-sm"
            value={drafts[key] ?? ""}
            onChange={e => setDraft(key, e.target.value)}
          />
        </td>
        <td style={{ width: 80 }}>
          <button
            className="btn btn-sm btn-primary"
            disabled={!dirty}
            onClick={() => save(key)}
          >
            {saved[key] ? "Saved ✓" : "Save"}
          </button>
        </td>
        <td className="text-muted" style={{ fontSize: "0.8rem" }}>{description}</td>
      </tr>
    );
  }

  function renderToggleRow(key: string, label: string, description: string) {
    const current = (drafts[key] ?? "False").toLowerCase();
    const checked = current === "true" || current === "1" || current === "yes";
    const dirty = drafts[key] !== (settings[key] ?? "False");
    return (
      <tr key={key}>
        <td style={{ width: 220, fontWeight: 500 }}>{label}</td>
        <td style={{ width: 200 }}>
          <div className="form-check form-switch mt-1">
            <input
              className="form-check-input"
              type="checkbox"
              role="switch"
              checked={checked}
              onChange={e => setDraft(key, e.target.checked ? "True" : "False")}
            />
            <label className="form-check-label">{checked ? "Enabled" : "Disabled"}</label>
          </div>
        </td>
        <td style={{ width: 80 }}>
          <button
            className="btn btn-sm btn-primary"
            disabled={!dirty}
            onClick={() => save(key)}
          >
            {saved[key] ? "Saved ✓" : "Save"}
          </button>
        </td>
        <td className="text-muted" style={{ fontSize: "0.8rem" }}>{description}</td>
      </tr>
    );
  }

  if (loading) return <Layout><p className="p-4">Loading…</p></Layout>;

  return (
    <Layout>
      <div className="container mt-4" style={{ maxWidth: 860 }}>
        <h1 className="mb-1">System Variables</h1>
        <p className="text-muted mb-4">Changes take effect immediately (cached values refresh within 2 minutes).</p>

        <h5 className="mb-2">System Settings</h5>
        <table className="table table-bordered align-middle mb-5">
          <tbody>
            {SYSTEM_KEYS.map(({ key, label, description }) =>
              renderRow(key, label, description, key.includes("fee") ? "number" : "number")
            )}
            {renderToggleRow("sms_send", "SMS Send", "When enabled, SMS messages are sent via ClickSend. When disabled, messages are logged but not delivered.")}
          </tbody>
        </table>

        <h5 className="mb-2">Quick-Login Test Accounts</h5>
        <p className="text-muted" style={{ fontSize: "0.85rem" }}>
          These are the credentials used by the Admin / Parent / Student / Tutor buttons in the navbar.
        </p>
        <table className="table table-bordered align-middle">
          <thead className="table-light">
            <tr>
              <th style={{ width: 80 }}>Role</th>
              <th>Username / Email</th>
              <th style={{ width: 80 }}></th>
              <th>Password</th>
              <th style={{ width: 80 }}></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {DEV_USER_ROLES.map(({ role, emailKey, passwordKey }) => {
              const emailDirty    = drafts[emailKey]    !== settings[emailKey];
              const passwordDirty = drafts[passwordKey] !== settings[passwordKey];
              const anyDirty = emailDirty || passwordDirty;
              return (
                <tr key={role}>
                  <td style={{ fontWeight: 500 }}>{role}</td>
                  <td>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      value={drafts[emailKey] ?? ""}
                      onChange={e => setDraft(emailKey, e.target.value)}
                    />
                  </td>
                  <td></td>
                  <td>
                    <input
                      type="text"
                      className="form-control form-control-sm"
                      value={drafts[passwordKey] ?? ""}
                      onChange={e => setDraft(passwordKey, e.target.value)}
                    />
                  </td>
                  <td>
                    <button
                      className="btn btn-sm btn-primary"
                      disabled={!anyDirty}
                      onClick={async () => {
                        if (emailDirty)    await save(emailKey);
                        if (passwordDirty) await save(passwordKey);
                      }}
                    >
                      {saved[emailKey] || saved[passwordKey] ? "Saved ✓" : "Save"}
                    </button>
                  </td>
                  <td></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
