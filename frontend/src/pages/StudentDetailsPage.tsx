import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { Layout, PageHeader } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

const LANGUAGE_LABELS: Record<string, string> = {
  en: "English",
  zh: "中文 (Chinese)",
  vi: "Tiếng Việt (Vietnamese)",
  ar: "العربية (Arabic)",
  ko: "한국어 (Korean)",
  hi: "हिन्दी (Hindi)",
  es: "Español (Spanish)",
  fr: "Français (French)",
  pt: "Português (Portuguese)",
  ja: "日本語 (Japanese)",
};

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="mb-3">
      <div style={{ fontSize: 12, color: "#8C8179", marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 15, color: "#2D2D2D" }}>{value || "Not set"}</div>
    </div>
  );
}

export function StudentDetailsPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [student, setStudent] = useState<any>(null);

  useEffect(() => {
    apiFetch(`/api/students/${id}/`)
      .then(r => r.json())
      .then(setStudent);
  }, [id]);

  if (!student) {
    return (
      <Layout>
        <div className="container mt-4">Loading…</div>
      </Layout>
    );
  }

  return (
    <Layout header={<PageHeader title="My Details" />}>
      <div className="container mt-4" style={{ maxWidth: 560 }}>
        <DetailRow label="Email" value={student.email} />
        <DetailRow label="Year Level" value={student.year_level} />
        <DetailRow label="Gender" value={
          student.gender === "male" ? "Male"
          : student.gender === "female" ? "Female"
          : student.gender === "other" ? "Other"
          : ""
        } />
        <DetailRow label="Mobile" value={student.mobile} />
        <DetailRow label="Address" value={student.address} />
        <DetailRow label="Question Language" value={LANGUAGE_LABELS[student.language] ?? student.language ?? ""} />
        <DetailRow label="Active" value={student.active ? "Yes" : "No"} />

        <button
          className="btn btn-outline-primary mt-2"
          onClick={() => navigate(`/students/${id}/edit?returnTo=/students/${id}/details`)}
        >
          Edit My Details
        </button>
      </div>
    </Layout>
  );
}
