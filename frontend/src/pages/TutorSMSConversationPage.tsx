import { Layout } from "./components/Layout";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { apiFetch } from "../utils/apiFetch";

interface SMSMessage {
  id: number;
  direction: "inbound" | "outbound";
  body: string;
  created_at: string;
  sent_at: string | null;
  delivered_at: string | null;
  status: string;
  phone_number: string | null;
}

interface SMSConversationThread {
  conversation_id: number;
  tutor_id: number;
  student_id: number;
  student_name: string;
  messages: SMSMessage[];
}

export function TutorSMSConversationPage() {
  const { id, conversationId } = useParams();
  const [thread, setThread] = useState<SMSConversationThread | null>(null);

  useEffect(() => {
    apiFetch(`/api/tutors/${id}/sms/conversation/${conversationId}/`)
      .then(res => res.json())
      .then(setThread);
  }, [id, conversationId]);

  if (!thread) return <Layout><div className="container mt-4">Loading…</div></Layout>;

  return (
    <Layout>
      <div className="container mt-4">
        <h3>Conversation with {thread.student_name}</h3>

        <div className="sms-thread mt-3">
          {[...thread.messages].sort((a, b) => b.created_at.localeCompare(a.created_at)).map(msg => (
            <div
              key={msg.id}
              className={msg.direction === "outbound" ? "sms-outbound" : "sms-inbound"}
              style={{
                textAlign: msg.direction === "outbound" ? "right" : "left",
                marginBottom: "12px"
              }}
            >
              <div
                style={{
                  display: "inline-block",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  background: msg.direction === "outbound" ? "#d1e7ff" : "#e9ecef"
                }}
              >
                {msg.body}
              </div>
              <div className="text-muted small">
                {new Date(msg.created_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  );
}