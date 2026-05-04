import { useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

export function TutorEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnTo = searchParams.get("returnTo") || `/tutors/${id}`;

  const [form, setForm] = useState({
    mobile: "",
    address: "",
    default_session_minutes: "",
    buffer_minutes: "",
    default_hourly_rate: "",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch(`/api/tutors/${id}/home/`)
      .then(res => res.json())
      .then(data => {
      console.log("EditPage data:", data)
        setForm({
          mobile: data.mobile || "",
          address: data.address || "",
          default_session_minutes: String(data.default_session_minutes || ""),
          buffer_minutes: String(data.buffer_minutes || ""),
          default_hourly_rate: String(data.default_hourly_rate || ""),
        });
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load tutor:", err);
        setError("Failed to load tutor details.");
        setLoading(false);
      });
  }, [id]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
  };

  const validate = () => {
    if (!form.mobile.trim()) return "Mobile number is required.";
    if (!form.address.trim()) return "Address is required.";
    if (!form.default_session_minutes.trim()) return "Default session minutes is required.";
    if (!form.buffer_minutes.trim()) return "Buffer minutes is required.";
    if (isNaN(Number(form.default_session_minutes))) return "Default session minutes must be a number.";
    if (isNaN(Number(form.buffer_minutes))) return "Buffer minutes must be a number.";
    if (form.default_hourly_rate.trim() && isNaN(Number(form.default_hourly_rate))) return "Hourly rate must be a number.";
    if (Number(form.default_hourly_rate) < 0) return "Hourly rate cannot be negative.";
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      await apiFetch(`/api/tutors/${id}/edit/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fields: {
            mobile: form.mobile,
            address: form.address,
            default_session_minutes: Number(form.default_session_minutes),
            buffer_minutes: Number(form.buffer_minutes),
            default_hourly_rate: Number(form.default_hourly_rate),
          },
        }),
      });


      navigate(returnTo);
    } catch (err) {
      console.error("Failed to save tutor:", err);
      setError("Failed to save changes.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="container mt-4">Loading…</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mt-4">
        <h2>Edit My Details</h2>

        {error && <div className="alert alert-danger">{error}</div>}

        <form onSubmit={handleSubmit} className="mt-3">

          <div className="mb-3">
            <label className="form-label">Mobile</label>
            <input
              type="text"
              name="mobile"
              className="form-control"
              value={form.mobile}
              onChange={handleChange}
            />
          </div>

          <div className="mb-3">
            <label className="form-label">Address</label>
            <input
              type="text"
              name="address"
              className="form-control"
              value={form.address}
              onChange={handleChange}
            />
          </div>

          <div className="mb-3">
            <label className="form-label">Default Session Minutes</label>
            <input
              type="number"
              name="default_session_minutes"
              className="form-control"
              value={form.default_session_minutes}
              onChange={handleChange}
              min={1}
            />
          </div>

          <div className="mb-3">
            <label className="form-label">Buffer Minutes</label>
            <input
              type="number"
              name="buffer_minutes"
              className="form-control"
              value={form.buffer_minutes}
              onChange={handleChange}
              min={0}
            />
          </div>

          <div className="mb-3">
            <label className="form-label">Default Hourly Rate ($)</label>
            <input
              type="number"
              name="default_hourly_rate"
              className="form-control"
              value={form.default_hourly_rate}
              onChange={handleChange}
              min={0}
              step="0.01"
            />
            <div className="form-text">Applied to new students when they are added.</div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? "Saving…" : "Save Changes"}
          </button>

          <button
            type="button"
            className="btn btn-secondary ms-2"
            onClick={() => navigate(returnTo)}
          >
            Cancel
          </button>
        </form>
      </div>
    </Layout>
  );
}