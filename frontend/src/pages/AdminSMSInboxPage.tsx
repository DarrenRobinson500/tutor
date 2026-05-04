import { Layout } from "./components/Layout";
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { apiFetch } from "../utils/apiFetch";

interface SMSConversationSummary {
  conversation_id: number;
  tutor_id: number;
  tutor_name: string;
  student_id: number;
  student_name: string;
  last_message: string;
  last_message_at: string;
}

export function AdminSMSInboxPage() {
  const [conversations, setConversations] = useState<SMSConversationSummary[]>([]);
  const navigate = useNavigate();

  useEffect(() => {
    apiFetch("/api/tutors/admin_sms/")
      .then(res => res.json())
      .then(setConversations);
  }, []);

  return (
    <Layout>
      <div className="container mt-4">
        <h2>SMS Messages</h2>

        {conversations.length === 0 && (
          <p className="text-muted">No conversations yet.</p>
        )}

        {conversations.map(c => (
          <div
            key={c.conversation_id}
            className="sms-convo-row"
            onClick={() => navigate(`/admin/sms/${c.conversation_id}`)}
            style={{ cursor: "pointer", padding: "12px", borderBottom: "1px solid #ddd" }}
          >
            <strong>{c.student_name}</strong>
            <span className="text-muted ms-2" style={{ fontSize: 13 }}>via {c.tutor_name}</span>
            <div className="text-muted small">{c.last_message}</div>
            <div className="text-muted small">{new Date(c.last_message_at).toLocaleString()}</div>
          </div>
        ))}
      </div>
    </Layout>
  );
}
