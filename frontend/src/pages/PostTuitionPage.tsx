import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface PaymentSummary {
  student_name: string;
  tutor_name: string;
  distributor_name: string | null;
  hourly_rate: string;
  session_minutes: number;
  amount_paid: string;
  amount_tutor: string;
  amount_platform: string;
  amount_distributor: string;
  account_tutor: string;
  account_distributor: string;
  date_tuition: string | null;
  already_applied: boolean;
  payment_id: number | null;
  has_outcome: boolean;
  pending_payment_confirmation: boolean;
  payment_parent_name: string | null;
}

interface FocusArea {
  id: number;
  skill_id: number;
  skill_code: string;
  skill_description: string;
  mastery: number;
}

interface SkillRow {
  id: number;
  code: string;
  description: string;
  depth: number;
  parent_id: number | null;
  children_count: number;
  cells: Record<string, { count: number | null; validated: number }>;
}

function SkillStars({ level }: { level: number }) {
  const standard = Math.min(level, 4);
  const bonus = Math.max(0, level - 4);
  const empty = 4 - standard;
  return (
    <span style={{ fontSize: 12, letterSpacing: 1 }}>
      <span style={{ color: "#f5a623" }}>{"★".repeat(standard)}</span>
      <span style={{ color: "#ccc" }}>{"★".repeat(empty)}</span>
      {bonus > 0 && <span style={{ color: "#a855f7" }}>{"✦".repeat(bonus)}</span>}
    </span>
  );
}

export function PostTuitionPage() {
  const { id: tutorId } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const studentId = searchParams.get("student_id");
  const jobId = searchParams.get("job_id");
  const bookingDate = searchParams.get("booking_date");

  const [studentName, setStudentName] = useState<string | null>(null);
  const [yearLevel, setYearLevel] = useState<string | null>(null);
  const [studentGender, setStudentGender] = useState<string | null>(null);
  const [genderLoading, setGenderLoading] = useState(false);
  // Step 1: progress message
  const [sessionProductive, setSessionProductive] = useState<boolean | null>(null);
  const [message, setMessage] = useState<string>("");
  const [parentMobile, setParentMobile] = useState<string | null>(null);
  const [parentName, setParentName] = useState<string | null>(null);
  const [messageLoading, setMessageLoading] = useState(false);
  const [messageSaving, setMessageSaving] = useState(false);
  const [messageSending, setMessageSending] = useState(false);
  const [messageSent, setMessageSent] = useState(false);
  const [messageError, setMessageError] = useState<string | null>(null);

  // Step 2: focus areas
  const [focusAreas, setFocusAreas] = useState<FocusArea[]>([]);
  const [syllabus, setSyllabus] = useState<SkillRow[]>([]);
  const [mastery, setMastery] = useState<Record<number, number>>({});
  const [focusLoading, setFocusLoading] = useState(false);
  const [focusAreasApproved, setFocusAreasApproved] = useState(false);

  // Step 3: payment
  const [payment, setPayment] = useState<PaymentSummary | null>(null);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [paymentApplying, setPaymentApplying] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);

  // Step 4: confirm receipt
  const [receiptConfirming, setReceiptConfirming] = useState(false);
  const [receiptConfirmed, setReceiptConfirmed] = useState(false);

  useEffect(() => {
    if (!studentId) return;
    apiFetch(`/api/students/${studentId}/`)
      .then((r) => r.json())
      .then((d) => {
        setStudentName(d.first_name ? `${d.first_name} ${d.last_name ?? ""}`.trim() : null);
        setYearLevel(d.year_level ?? null);
        setStudentGender(d.gender || null);
      })
      .catch(() => {});
  }, [studentId]);

  async function handleGenderSelect(g: string) {
    if (!studentId) return;
    setGenderLoading(true);
    await apiFetch(`/api/students/${studentId}/edit/`, {
      method: "POST",
      body: JSON.stringify({ fields: { gender: g } }),
    }).catch(() => {});
    setStudentGender(g);
    setGenderLoading(false);
  }

  useEffect(() => {
    if (!jobId || sessionProductive === null) return;
    setMessageLoading(true);
    apiFetch(`/api/jobs/${jobId}/progress_message/?productive=${sessionProductive}`)
      .then((r) => r.json())
      .then((d) => {
        setMessage(d.message ?? "");
        setParentMobile(d.parent_mobile ?? null);
        setParentName(d.parent_name ?? null);
      })
      .catch(() => setMessageError("Failed to load message."))
      .finally(() => setMessageLoading(false));
  }, [jobId, sessionProductive]);

  useEffect(() => {
    if (!jobId) return;
    setPaymentLoading(true);
    apiFetch(`/api/jobs/${jobId}/payment_summary/`)
      .then((r) => r.json())
      .then((d: PaymentSummary) => setPayment(d))
      .catch(() => setPaymentError("Failed to load payment summary."))
      .finally(() => setPaymentLoading(false));
  }, [jobId]);

  // Load focus areas (re-fetched after add/remove)
  function loadFocusAreas() {
    if (!studentId) return;
    apiFetch(`/api/focus-areas/?student_id=${studentId}`)
      .then((r) => r.json())
      .then((d) => { if (Array.isArray(d)) setFocusAreas(d); })
      .catch(() => {});
  }

  useEffect(() => {
    if (!studentId) return;
    setFocusLoading(true);
    loadFocusAreas();
    setFocusLoading(false);
  }, [studentId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!studentId || !yearLevel) return;
    apiFetch(`/api/skills/matrix/?grade=${yearLevel}&student_id=${studentId}`)
      .then((r) => r.json())
      .then((d) => {
        setSyllabus(d.skills ?? []);
        // mastery map: skill_id → level
        const m: Record<number, number> = {};
        for (const [id, val] of Object.entries(d.mastery ?? {})) {
          m[Number(id)] = (val as any).mastery ?? 0;
        }
        setMastery(m);
      })
      .catch(() => {});
  }, [studentId, yearLevel]);

  async function handleRemoveFocusArea(faId: number) {
    await apiFetch(`/api/focus-areas/${faId}/`, { method: "DELETE" });
    setFocusAreas((prev) => prev.filter((fa) => fa.id !== faId));
  }

  async function handleAddFocusArea(skillId: number) {
    if (!studentId) return;
    const r = await apiFetch(`/api/focus-areas/`, {
      method: "POST",
      body: JSON.stringify({ student_id: studentId, skill_id: skillId }),
    });
    const d = await r.json();
    if (d.id) loadFocusAreas();
  }

  function formatDate(dateStr: string | null) {
    if (!dateStr) return null;
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-AU", { day: "numeric", month: "short" });
  }

  const dateLabel = formatDate(bookingDate);

  function formatCurrency(val: string) {
    return `$${parseFloat(val).toFixed(2)}`;
  }

  async function handleSaveMessage() {
    if (!jobId) return;
    setMessageSaving(true);
    setMessageError(null);
    try {
      await apiFetch(`/api/jobs/${jobId}/save_progress_message/`, {
        method: "POST",
        body: JSON.stringify({ message }),
      });
    } catch {
      setMessageError("Failed to save message.");
    } finally {
      setMessageSaving(false);
    }
  }

  async function completeJob(extraData: Record<string, unknown> = {}) {
    if (!jobId) return;
    await apiFetch(`/api/jobs/${jobId}/complete/`, {
      method: "POST",
      body: JSON.stringify(extraData),
    });
    navigate(`/tutors/${tutorId}/`);
  }

  async function handleSendMessage() {
    if (!jobId) return;
    setMessageSending(true);
    setMessageError(null);
    try {
      await apiFetch(`/api/jobs/${jobId}/save_progress_message/`, {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      await apiFetch(`/api/jobs/${jobId}/send_progress_message/`, { method: "POST" });
      setMessageSent(true);
    } catch {
      setMessageError("Failed to send message.");
    } finally {
      setMessageSending(false);
    }
  }

  function handleApproveFocusAreas() {
    setFocusAreasApproved(true);
  }

  async function handleConfirmReceipt() {
    if (!payment?.payment_id) return;
    setReceiptConfirming(true);
    try {
      await apiFetch(`/api/payments/${payment.payment_id}/confirm_receipt/`, { method: "POST" });
      setReceiptConfirmed(true);
      setPayment(prev => prev ? { ...prev, pending_payment_confirmation: false } : prev);
    } catch {
      // silently ignore — confirmation can be done from Payments page too
    } finally {
      setReceiptConfirming(false);
    }
  }

  async function handleRequestPayment() {
    if (!jobId) return;
    setPaymentApplying(true);
    setPaymentError(null);
    try {
      const r = await apiFetch(`/api/jobs/${jobId}/apply_payment/`, { method: "POST" });
      const d = await r.json();
      if (d.ok) {
        await completeJob({
          parent_message: message,
          focus_area_next_ids: focusAreas.map((fa) => fa.skill_id),
        });
      } else {
        setPaymentError(d.error ?? "Failed to request payment.");
        setPaymentApplying(false);
      }
    } catch {
      setPaymentError("Failed to request payment.");
      setPaymentApplying(false);
    }
  }

  const focusAreaSkillIds = new Set(focusAreas.map((fa) => fa.skill_id));

  return (
    <Layout>
      <div className="container py-4" style={{ maxWidth: 780 }}>
        <h2 className="mb-1">
          Post Tuition
          {studentName && ` — ${studentName}`}
          {dateLabel && <span className="text-muted fw-normal"> [{dateLabel}]</span>}
        </h2>
        <p className="text-muted mb-4">Complete the following steps after the session.</p>

        {/* ── Step 1: Parent update message ── */}
        <div className="card mb-4">
          <div className="card-header d-flex align-items-center gap-2">
            <span className="badge bg-primary">1</span>
            <span className="fw-semibold">Send Progress Message</span>
            {messageSent && <span className="badge bg-primary ms-auto">Sent</span>}
          </div>
          <div className="card-body">
            {!studentGender ? (
              <>
                <p className="mb-3">
                  Is <strong>{studentName || "the student"}</strong> male or female?
                </p>
                <div className="d-flex gap-2">
                  <button
                    className="btn btn-outline-primary"
                    onClick={() => handleGenderSelect("male")}
                    disabled={genderLoading}
                  >
                    Male
                  </button>
                  <button
                    className="btn btn-outline-primary"
                    onClick={() => handleGenderSelect("female")}
                    disabled={genderLoading}
                  >
                    Female
                  </button>
                  <button
                    className="btn btn-outline-secondary"
                    onClick={() => handleGenderSelect("other")}
                    disabled={genderLoading}
                  >
                    Other
                  </button>
                </div>
              </>
            ) : sessionProductive === null ? (
              <>
                <p className="mb-3">Was this session productive?</p>
                <div className="d-flex gap-2">
                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => setSessionProductive(true)}
                  >
                    Yes
                  </button>
                  <button
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => setSessionProductive(false)}
                  >
                    No
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="text-muted mb-3">
                  Review the session summary message below, edit if needed, then send it to the parent.
                </p>
                {messageLoading ? (
                  <div className="text-center py-3">
                    <div className="spinner-border spinner-border-sm text-secondary" role="status" />
                  </div>
                ) : (
                  <>
                    <textarea
                      className="form-control mb-2"
                      rows={5}
                      value={message}
                      onChange={(e) => setMessage(e.target.value)}
                      disabled={messageSending || messageSent}
                    />
                    {parentMobile && (
                      <div className="text-muted mb-2" style={{ fontSize: 13 }}>
                        This message will be sent to{parentName ? ` ${parentName}` : ""} on {parentMobile.replace(/(\d{4})(\d{3})(\d{3})/, "$1 $2 $3")}
                      </div>
                    )}
                    {messageError && (
                      <div className="alert alert-danger py-2 mb-2" style={{ fontSize: 13 }}>
                        {messageError}
                      </div>
                    )}
                    <div className="d-flex gap-2">
                      <button
                        className="btn btn-outline-secondary btn-sm"
                        onClick={handleSaveMessage}
                        disabled={messageSaving || !message.trim() || messageSent}
                      >
                        {messageSaving ? "Saving…" : "Save Draft"}
                      </button>
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={handleSendMessage}
                        disabled={messageSending || !message.trim() || messageSent}
                      >
                        {messageSent ? "Sent" : messageSending ? "Sending…" : "Send to Parent"}
                      </button>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </div>

        {/* ── Step 2: Focus areas ── */}
        <div className="card mb-4">
          <div className="card-header d-flex align-items-center gap-2">
            <span className="badge bg-primary">2</span>
            <span className="fw-semibold">Update Student Focus Areas</span>
            {focusAreasApproved && <span className="badge bg-primary ms-auto">Approved</span>}
          </div>
          <div className="card-body">
            {focusLoading ? (
              <div className="text-center py-3">
                <div className="spinner-border spinner-border-sm text-secondary" role="status" />
              </div>
            ) : (
              <>
                {/* Current focus areas */}
                <div className="mb-3">
                  <div className="fw-semibold mb-2" style={{ fontSize: 14 }}>Current Focus Areas</div>
                  {focusAreas.length === 0 ? (
                    <div className="text-muted" style={{ fontSize: 13 }}>No focus areas set.</div>
                  ) : (
                    <div>
                      {focusAreas.map((fa) => (
                        <div
                          key={fa.id}
                          className="d-flex align-items-center justify-content-between py-1 px-2 mb-1 rounded"
                          style={{ background: "#f8f9fa", fontSize: 13 }}
                        >
                          <span>{fa.skill_description}</span>
                          <div className="d-flex align-items-center gap-2">
                            <SkillStars level={fa.mastery} />
                            <button
                              className="btn btn-outline-danger btn-sm py-0 px-2"
                              style={{ fontSize: 12 }}
                              onClick={() => handleRemoveFocusArea(fa.id)}
                              disabled={focusAreasApproved}
                            >
                              Remove
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {syllabus.length > 0 && !focusAreasApproved && (
                  <div className="mt-3">
                    <div className="fw-semibold mb-2" style={{ fontSize: 14 }}>Syllabus</div>
                    <div style={{ maxHeight: 320, overflowY: "auto", border: "1px solid #dee2e6", borderRadius: 4 }}>
                      <table className="table table-sm mb-0" style={{ fontSize: 12 }}>
                        <tbody>
                          {syllabus.map((skill) => {
                            const isLeaf = skill.children_count === 0;
                            const alreadyAdded = focusAreaSkillIds.has(skill.id);
                            const gradeStr = yearLevel ?? "";
                            const cell = skill.cells[gradeStr];
                            const hasTemplates = cell ? cell.validated > 0 : false;
                            const masteryLevel = Math.round(mastery[skill.id] ?? 0);
                            return (
                              <tr key={skill.id} style={{ background: isLeaf ? undefined : "#f8f9fa" }}>
                                <td style={{ paddingLeft: `${skill.depth * 16 + 8}px`, fontWeight: isLeaf ? undefined : 600, color: isLeaf ? undefined : "#444" }}>
                                  {skill.description}
                                </td>
                                <td style={{ width: 80, whiteSpace: "nowrap" }}>
                                  {isLeaf && <SkillStars level={masteryLevel} />}
                                </td>
                                <td style={{ width: 70, textAlign: "right" }}>
                                  {isLeaf && hasTemplates && (
                                    alreadyAdded ? (
                                      <span className="text-muted" style={{ fontSize: 11 }}>Added</span>
                                    ) : (
                                      <button
                                        className="btn btn-outline-primary btn-sm py-0 px-2"
                                        style={{ fontSize: 11 }}
                                        onClick={() => handleAddFocusArea(skill.id)}
                                      >
                                        Add
                                      </button>
                                    )
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Approve button */}
                <div className="mt-3">
                  {payment && !payment.has_outcome ? (
                    <div className="alert alert-warning py-2 mb-0" style={{ fontSize: 13 }}>
                      No session record found — focus areas cannot be saved. This job may have been created before session tracking was enabled.
                    </div>
                  ) : (
                    <button
                      className={`btn btn-sm ${focusAreasApproved ? "btn-primary" : "btn-primary"}`}
                      onClick={handleApproveFocusAreas}
                      disabled={focusAreasApproved || paymentLoading || focusAreas.length === 0}
                    >
                      {focusAreasApproved ? "Approved" : "Approve Focus Areas"}
                    </button>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {/* ── Step 3: Payment ── */}
        <div className="card mb-4">
          <div className="card-header d-flex align-items-center gap-2">
            <span className="badge bg-primary">3</span>
            <span className="fw-semibold">Request Payment</span>
            {payment?.already_applied && <span className="badge bg-primary ms-auto">Applied</span>}
          </div>
          <div className="card-body">
            {!messageSent || !focusAreasApproved ? (
              <div className="alert alert-warning py-2 mb-0" style={{ fontSize: 13 }}>
                Complete steps 1 and 2 before requesting payment.
              </div>
            ) : paymentLoading ? (
              <div className="text-center py-3">
                <div className="spinner-border spinner-border-sm text-secondary" role="status" />
              </div>
            ) : payment ? (
              <>
                <table className="table table-sm mb-3" style={{ fontSize: 14 }}>
                  <tbody>
                    <tr>
                      <td className="text-muted" style={{ width: "40%" }}>Student</td>
                      <td>{payment.student_name}</td>
                    </tr>
                    <tr>
                      <td className="text-muted">Session</td>
                      <td>{payment.session_minutes} min @ {formatCurrency(payment.hourly_rate)}/hr</td>
                    </tr>
                    <tr>
                      <td className="text-muted">Date</td>
                      <td>{formatDate(payment.date_tuition) ?? "—"}</td>
                    </tr>
                    <tr>
                      <td className="text-muted fw-semibold">Amount charged</td>
                      <td className="fw-semibold">{formatCurrency(payment.amount_paid)}</td>
                    </tr>
                  </tbody>
                </table>
                <div className="p-3 rounded mb-3" style={{ background: "#f8f9fa", fontSize: 14 }}>
                  <div className="fw-semibold mb-2">Split</div>
                  <div className="d-flex justify-content-between mb-1">
                    <span>Tutor ({payment.tutor_name})</span>
                    <span>{formatCurrency(payment.amount_tutor)}</span>
                  </div>
                  {payment.account_tutor && (
                    <div className="text-muted mb-2" style={{ fontSize: 12 }}>
                      Account: {payment.account_tutor}
                    </div>
                  )}
                  {payment.distributor_name && (
                    <>
                      <div className="d-flex justify-content-between mb-1">
                        <span>Distributor ({payment.distributor_name})</span>
                        <span>{formatCurrency(payment.amount_distributor)}</span>
                      </div>
                      {payment.account_distributor && (
                        <div className="text-muted mb-2" style={{ fontSize: 12 }}>
                          Account: {payment.account_distributor}
                        </div>
                      )}
                    </>
                  )}
                  <div className="d-flex justify-content-between">
                    <span>Platform</span>
                    <span>{formatCurrency(payment.amount_platform)}</span>
                  </div>
                </div>
                {paymentError && (
                  <div className="alert alert-danger py-2 mb-2" style={{ fontSize: 13 }}>
                    {paymentError}
                  </div>
                )}
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleRequestPayment}
                  disabled={paymentApplying || payment.already_applied}
                >
                  {payment.already_applied
                    ? `Payment Applied (#${payment.payment_id})`
                    : paymentApplying ? "Requesting…" : "Request Payment"}
                </button>
              </>
            ) : (
              <p className="text-muted mb-0">No payment information available.</p>
            )}
          </div>
        </div>

        {/* ── Step 4: Confirm receipt (only shown when parent has paid but tutor hasn't confirmed) ── */}
        {payment && (payment.pending_payment_confirmation || receiptConfirmed) && (
          <div className="card mb-4">
            <div className="card-header d-flex align-items-center gap-2">
              <span className="badge bg-primary">4</span>
              <span className="fw-semibold">Confirm Payment Received</span>
              {receiptConfirmed && <span className="badge bg-primary ms-auto">Confirmed</span>}
            </div>
            <div className="card-body">
              {receiptConfirmed ? (
                <p className="mb-0 text-success" style={{ fontSize: 14 }}>
                  Payment confirmed — thank you.
                </p>
              ) : (
                <>
                  <p className="mb-3" style={{ fontSize: 14 }}>
                    Have you received payment from{" "}
                    <strong>{payment.payment_parent_name ?? "the parent"}</strong> for the session
                    {payment.date_tuition ? ` on ${formatDate(payment.date_tuition)}` : ""} with{" "}
                    <strong>{payment.student_name}</strong>?
                  </p>
                  <div className="d-flex gap-2">
                    <button
                      className="btn btn-success btn-sm"
                      onClick={handleConfirmReceipt}
                      disabled={receiptConfirming}
                    >
                      {receiptConfirming ? "Confirming…" : "Yes, I've received it"}
                    </button>
                    <button
                      className="btn btn-outline-secondary btn-sm"
                      onClick={() => setPayment(prev => prev ? { ...prev, pending_payment_confirmation: false } : prev)}
                    >
                      Not yet
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}

      </div>
    </Layout>
  );
}
