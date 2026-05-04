import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../../utils/apiFetch";

interface CallData {
  room_name: string;
  tutor_name: string;
}

export function IncomingCallBanner() {
  const [call, setCall] = useState<CallData | null>(null);
  const [dismissed, setDismissed] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;

    const poll = async () => {
      try {
        const res = await apiFetch("/api/sessions/incoming_call/");
        const data = await res.json();
        if (!active) return;
        if (data.room_name && data.room_name !== dismissed) {
          setCall(data);
        } else if (!data.room_name) {
          setCall(null);
        }
      } catch {}
    };

    poll();
    const interval = setInterval(poll, 6000);
    return () => { active = false; clearInterval(interval); };
  }, [dismissed]);

  if (!call) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: 70,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 2000,
        background: "#1a7a3f",
        color: "#fff",
        borderRadius: 10,
        padding: "14px 24px",
        boxShadow: "0 4px 24px rgba(0,0,0,0.3)",
        display: "flex",
        alignItems: "center",
        gap: 16,
        minWidth: 320,
      }}
    >
      <span style={{ fontSize: 22 }}>📞</span>
      <div style={{ flex: 1 }}>
        <strong>{call.tutor_name}</strong> is calling you!
      </div>
      <button
        className="btn btn-light btn-sm"
        style={{ fontWeight: 600 }}
        onClick={() => {
          setDismissed(call.room_name);
          setCall(null);
          navigate(`/session/${call.room_name}`);
        }}
      >
        Join
      </button>
      <button
        className="btn btn-outline-light btn-sm"
        onClick={() => {
          setDismissed(call.room_name);
          setCall(null);
        }}
      >
        Dismiss
      </button>
    </div>
  );
}
