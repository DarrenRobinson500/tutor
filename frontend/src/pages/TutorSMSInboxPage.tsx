import { Layout } from "./components/Layout";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { apiFetch } from "../utils/apiFetch";

interface SMSConversationSummary {
  conversation_id: number;
  student_id: number;
  student_name: string;
  last_message: string;
  last_message_at: string;
}

export function TutorSMSInboxPage() {
  const { id } = useParams();
  const [conversations, setConversations] = useState<SMSConversationSummary[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    apiFetch(`/api/tutors/${id}/sms/`)
      .then(res => res.json())
      .then(setConversations);
  }, [id]);

  return (
    <Layout>
      <div className="container mt-4">
        <h2>SMS Messages</h2>

        {conversations.map(c => (
          <div
            key={c.conversation_id}
            className="sms-convo-row"
            onClick={() => navigate(`/tutors/${id}/sms/${c.conversation_id}`)}
            style={{ cursor: "pointer", padding: "12px", borderBottom: "1px solid #ddd" }}
          >
            <strong>{c.student_name}</strong>
            <div className="text-muted small">{c.last_message}</div>
            <div className="text-muted small">{new Date(c.last_message_at).toLocaleString()}</div>
          </div>
        ))}
      </div>
    </Layout>
  );
}