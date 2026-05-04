import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { useYears } from "../utils/useYears";

export function StudentEditPage() {
  const { studentId } = useParams();
  const years = useYears();
  const navigate = useNavigate();

  // Read returnTo from query string
  const params = new URLSearchParams(window.location.search);
  const returnTo = params.get("returnTo") || `/student/${studentId}`;

  const [yearLevel, setYearLevel] = useState("");
  const [active, setActive] = useState(true);
  const [mobile, setMobile] = useState("");
  const [address, setAddress] = useState("");
  const [language, setLanguage] = useState("en");

  const LANGUAGE_OPTIONS = [
    { code: "en", label: "English" },
    { code: "zh", label: "中文 (Chinese)" },
    { code: "vi", label: "Tiếng Việt (Vietnamese)" },
    { code: "ar", label: "العربية (Arabic)" },
    { code: "ko", label: "한국어 (Korean)" },
    { code: "hi", label: "हिन्दी (Hindi)" },
    { code: "es", label: "Español (Spanish)" },
    { code: "fr", label: "Français (French)" },
    { code: "pt", label: "Português (Portuguese)" },
    { code: "ja", label: "日本語 (Japanese)" },
  ];

  const [loading, setLoading] = useState(true);

useEffect(() => {
  const url = `/api/students/${studentId}/`;

  console.log("Fetching:", url);

  apiFetch(url)
    .then(async (res) => {
      console.log("Raw response from", url, res);

      const data = await res.json();
      console.log("Parsed JSON from", url, data);

      setYearLevel(data.year_level || "");
      setMobile(data.mobile || "");
      setAddress(data.address || "");
      setActive(data.active);
      setLanguage(data.language || "en");
    })
    .catch((err) => {
      console.error("Error fetching", url, err);
    })
    .finally(() => setLoading(false));
}, [studentId]);


  const handleSave = async () => {
    await apiFetch(`/api/students/${studentId}/edit/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fields: {
          year_level: yearLevel,
          mobile: mobile,
          address: address,
          active: active,
          language: language,
        },
      }),
    });

    navigate(returnTo);
  };

  if (loading) return <p>Loading…</p>;

  return (
    <div className="container mt-4">
      <h1>Edit Student Details</h1>

      <div className="mb-3">
        <label className="form-label">Year Level</label>
        <select
          className="form-select"
          value={yearLevel}
          onChange={(e) => setYearLevel(e.target.value)}
        >
          <option value="">— select —</option>
          {years.map((y) => (
            <option key={y.code} value={y.code}>{y.label}</option>
          ))}
        </select>
      </div>

      <div className="mb-3">
        <label className="form-label">Mobile</label>
        <input
          type="text"
          className="form-control"
          value={mobile}
          onChange={(e) => setMobile(e.target.value)}
        />
      </div>

      <div className="mb-3">
        <label className="form-label">Address</label>
        <textarea
          className="form-control"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
        />
      </div>

      <div className="mb-3">
        <label className="form-label">Question Language</label>
        <select
          className="form-select"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        >
          {LANGUAGE_OPTIONS.map((opt) => (
            <option key={opt.code} value={opt.code}>{opt.label}</option>
          ))}
        </select>
        <div className="form-text">Questions will be shown in this language during learning sessions.</div>
      </div>

      <div className="form-check mb-3">
        <input
          className="form-check-input"
          type="checkbox"
          id="activeCheck"
          checked={active}
          onChange={(e) => setActive(e.target.checked)}
        />
        <label className="form-check-label" htmlFor="activeCheck">
          Active student
        </label>
      </div>

      <button className="btn btn-primary me-2" onClick={handleSave}>
        Save
      </button>

      <button
        className="btn btn-outline-secondary"
        onClick={() => navigate(returnTo)}
      >
        Cancel
      </button>
    </div>
  );
}