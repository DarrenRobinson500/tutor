import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiFetch } from "../../utils/apiFetch";
import { dashboardPath } from "../../utils/dashboardPath";

interface Props {
  parentId: string | number;
  /** Pass if already known — avoids an extra API call. */
  hasTutor?: boolean;
}

export function ParentNav({ parentId, hasTutor: hasTutorProp }: Props) {
  const navigate = useNavigate();
  const storedUser = (() => { try { return JSON.parse(localStorage.getItem("user") ?? "{}"); } catch { return {}; } })();
  const parentName = [storedUser.first_name, storedUser.last_name].filter(Boolean).join(" ");

  const [hasTutor, setHasTutor] = useState<boolean>(hasTutorProp ?? false);

  useEffect(() => {
    if (hasTutorProp !== undefined) { setHasTutor(hasTutorProp); return; }
    apiFetch("/api/auth/parent_home/")
      .then(r => r.json())
      .then(d => setHasTutor((d.children ?? []).some((c: any) => c.tutor_name)))
      .catch(() => {});
  }, [hasTutorProp]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleLogout() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("user");
    navigate("/login?tab=parent");
  }

  return (
    <nav className="ph-nav">
      <div className="ph-nav-left">
        <Link to={dashboardPath()} className="ph-nav-logo">
          <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
        </Link>
        <div className="ph-nav-links">
          <Link to={`/parents/${parentId}`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Home</Link>
          {hasTutor && <Link to={`/parents/${parentId}/bookings`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Bookings</Link>}
          {hasTutor && <Link to={`/parents/${parentId}/payments`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Payments</Link>}
          <Link to={`/parents/${parentId}/principles`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Helping your child</Link>
          <Link to={`/parents/${parentId}/feedback`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Feedback</Link>
        </div>
      </div>
      <div className="ph-nav-right">
        {parentName && <span className="ph-nav-user">{parentName}</span>}
        <button className="ph-nav-logout" onClick={handleLogout}>Sign out</button>
      </div>
    </nav>
  );
}
