import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

/**
 * Public page that exchanges a one-time assessment token for a student JWT,
 * stores it in localStorage, and immediately redirects to the test page.
 *
 * URL: /assessment-launch?token=<uuid>&student_id=<id>
 */
export default function AssessmentLaunchPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    const studentId = searchParams.get("student_id");

    if (!token || !studentId) {
      setError("Invalid assessment link.");
      return;
    }

    const API_URL = (process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "");
    fetch(`${API_URL}/api/auth/exchange_token/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.error) {
          setError(data.error);
          return;
        }
        localStorage.setItem("access", data.access);
        localStorage.setItem("refresh", data.refresh);
        localStorage.setItem("user", JSON.stringify(data.user));
        navigate(`/students/${studentId}/test`, { replace: true });
      })
      .catch(() => {
        setError("Something went wrong. Please try again.");
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  if (error) {
    return (
      <div style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "Inter, system-ui, sans-serif",
        background: "#FFFBF5",
        padding: "2rem",
        textAlign: "center",
      }}>
        <img src="/subjectmatter_logo.svg" alt="SubjectMatter" style={{ height: 64, marginBottom: "2rem" }} />
        <div style={{
          background: "#FDECEA",
          color: "#C0392B",
          border: "1px solid #f5c6cb",
          borderRadius: 8,
          padding: "1rem 1.5rem",
          maxWidth: 400,
          marginBottom: "1.5rem",
        }}>
          {error}
        </div>
        <a href="/" style={{ color: "#FF8C42", fontSize: "0.875rem" }}>← Back to home</a>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "Inter, system-ui, sans-serif",
      background: "#FFFBF5",
    }}>
      <img src="/subjectmatter_logo.svg" alt="SubjectMatter" style={{ height: 64, marginBottom: "2rem" }} />
      <p style={{ color: "#5C5249", fontSize: "1rem" }}>Starting assessment…</p>
    </div>
  );
}
