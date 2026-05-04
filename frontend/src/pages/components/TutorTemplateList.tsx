import { useEffect, useState, useRef } from "react";
import { apiFetch, apiFetchJson } from "../../utils/apiFetch"


export function TutorTemplateList({ tutorId }: { tutorId: string }) {
  const [templates, setTemplates] = useState([]);

  useEffect(() => {
    apiFetch(`/api/tutors/${tutorId}/templates/`)
      .then(res => res.json())
      .then(data => setTemplates(data));
  }, [tutorId]);

  return (
    <ul className="list-group">
      {templates.map((t: any) => (
        <li key={t.id} className="list-group-item">
          <a href={`/templates/${t.id}`}>{t.name || t.subject}</a>
        </li>
      ))}
    </ul>

  );
}