import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { dashboardPath } from "../utils/dashboardPath";
import "./DistributorHomePage.css";

interface Child {
  id: number;
  first_name: string;
  last_name: string;
  year_level: string | null;
}

interface Parent {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  joined: string;
  children: Child[];
}

interface DistributorData {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  referral_code: string | null;
  approved: boolean;
  parents: Parent[];
  parent_count: number;
  student_count: number;
}

export default function DistributorHomePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DistributorData | null>(null);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  function handleLogout() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("user");
    navigate("/distributors");
  }

  useEffect(() => {
    apiFetch(`/api/distributors/${id}/`)
      .then((r) => r.json())
      .then((d) => {
        if (d.error) setError(d.error);
        else setData(d);
      })
      .catch(() => setError("Failed to load dashboard."));
  }, [id]);

  const referralUrl = data?.referral_code
    ? `${window.location.origin}/ref/${data.referral_code}`
    : null;

  function copyLink() {
    if (!referralUrl) return;
    navigator.clipboard.writeText(referralUrl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  if (error) {
    return (
      <div className="dh-root">
        <div className="dh-error">{error}</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="dh-root">
        <div className="dh-loading">Loading…</div>
      </div>
    );
  }

  return (
    <div className="dh-root">

      {/* ── Header ─────────────────────────────────── */}
      <header className="dh-header">
        <div className="dh-header-inner">
          <Link to={dashboardPath()} className="dh-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </Link>
          <div className="dh-header-right">
            <span className="dh-header-name">
              {data.first_name} {data.last_name}
            </span>
            {!data.approved && (
              <span className="dh-pending-badge">Pending approval</span>
            )}
            <button className="dh-logout-btn" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="dh-main">
        <div className="dh-main-inner">

          {/* ── Page title ─────────────────────────── */}
          <div className="dh-page-title">
            <h1>Your distributor dashboard</h1>
            <p>Track the parents and students you've brought to SubjectMatter.</p>
          </div>

          {/* ── Stats row ──────────────────────────── */}
          <div className="dh-stats">
            <div className="dh-stat-card">
              <div className="dh-stat-value">{data.parent_count}</div>
              <div className="dh-stat-label">Parents referred</div>
            </div>
            <div className="dh-stat-card">
              <div className="dh-stat-value">{data.student_count}</div>
              <div className="dh-stat-label">Students acquired</div>
            </div>
            <div className="dh-stat-card dh-stat-placeholder">
              <div className="dh-stat-value">—</div>
              <div className="dh-stat-label">Revenue (coming soon)</div>
            </div>
          </div>

          {/* ── Referral link ──────────────────────── */}
          {referralUrl && (
            <div className="dh-referral-section">
              <div className="dh-section-label">Your referral link</div>
              <p className="dh-referral-hint">
                Share this link. This is a link to the parent and student landing page, which leads to their registration page. Any parent who signs up through it is attributed to you.
              </p>
              <div className="dh-referral-box">
                <span className="dh-referral-url">{referralUrl}</span>
                <button className="dh-copy-btn" onClick={copyLink}>
                  {copied ? "Copied!" : "Copy"}
                </button>
              </div>
            </div>
          )}

          {/* ── Parents table ──────────────────────── */}
          <div className="dh-parents-section">
            <div className="dh-section-label">Referred parents &amp; students</div>

            {data.parents.length === 0 ? (
              <div className="dh-empty">
                No parents yet. Share your referral link to get started.
              </div>
            ) : (
              <div className="dh-parents-list">
                {data.parents.map((parent) => (
                  <div key={parent.id} className="dh-parent-card">
                    <div className="dh-parent-header">
                      <div className="dh-parent-avatar">
                        {parent.first_name[0]}{parent.last_name[0]}
                      </div>
                      <div className="dh-parent-info">
                        <div className="dh-parent-name">
                          {parent.first_name} {parent.last_name}
                        </div>
                        <div className="dh-parent-meta">
                          {parent.email} · Joined {parent.joined}
                        </div>
                      </div>
                      <div className="dh-child-count">
                        {parent.children.length}{" "}
                        {parent.children.length === 1 ? "student" : "students"}
                      </div>
                    </div>

                    {parent.children.length > 0 && (
                      <div className="dh-children">
                        {parent.children.map((child) => (
                          <div key={child.id} className="dh-child-row">
                            <span className="dh-child-name">
                              {child.first_name} {child.last_name}
                            </span>
                            {child.year_level && (
                              <span className="dh-child-year">Year {child.year_level}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </main>
    </div>
  );
}
