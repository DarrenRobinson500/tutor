import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { LiveKitRoom, RoomAudioRenderer } from "@livekit/components-react";
import "@livekit/components-styles";
import { VideoPanel } from "./components/VideoPanel";
import { WhiteboardPanel } from "./components/WhiteboardPanel";
import { QuestionPanel } from "./components/QuestionPanel";
import { apiFetch } from "../utils/apiFetch";
import { usePreferenceStore } from "../utils/pref";

// Cast to any to handle React 19 / @livekit/components-react type incompatibility
const LKRoom = LiveKitRoom as React.ComponentType<any>;

export function TutoringRoomPage() {
  const { roomName } = useParams<{ roomName: string }>();
  const navigate = useNavigate();
  const [token, setToken] = useState<string | null>(null);
  const [livekitUrl, setLivekitUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [joined, setJoined] = useState(false);

  const pref = usePreferenceStore();
  const prefLoaded = usePreferenceStore((s) => s.loaded);
  const [showVideo, setShowVideo] = useState(true);
  const [showWhiteboard, setShowWhiteboard] = useState(true);
  const [showQuestion, setShowQuestion] = useState(true);

  // Apply stored preferences once they have loaded from the backend
  useEffect(() => {
    if (!prefLoaded) return;
    const v = pref.get("chat_show_video");
    const w = pref.get("chat_show_whiteboard");
    const q = pref.get("chat_show_question");
    if (v !== undefined) setShowVideo(v);
    if (w !== undefined) setShowWhiteboard(w);
    if (q !== undefined) setShowQuestion(q);
  }, [prefLoaded]); // eslint-disable-line react-hooks/exhaustive-deps

  // Parse isTutor and studentId from room name (format: t{tutor_id}-s{student_id})
  const storedUser = localStorage.getItem("user");
  const user = storedUser ? JSON.parse(storedUser) : null;
  const isTutor = user?.role === "tutor" || user?.role === "admin";
  const roomMatch = roomName?.match(/^t(\d+)-s(\d+)$/);
  const studentId = roomMatch ? parseInt(roomMatch[2], 10) : undefined;

  useEffect(() => {
    if (!roomName) return;
    apiFetch(`/api/sessions/token/`, {
      method: "POST",
      body: JSON.stringify({ room_name: roomName }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.error) {
          setError(data.error);
        } else {
          setToken(data.token);
          setLivekitUrl(data.livekit_url);
        }
      })
      .catch(() => setError("Failed to connect to session."));
  }, [roomName]);

  if (error) {
    return (
      <div className="container mt-5">
        <div className="alert alert-danger">{error}</div>
        <button className="btn btn-secondary" onClick={() => navigate(-1)}>Go back</button>
      </div>
    );
  }

  if (!token || !livekitUrl) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#1a1a1a" }}>
        <div style={{ textAlign: "center", color: "#fff" }}>
          <div className="spinner-border text-light" role="status" />
          <div className="mt-3" style={{ color: "#aaa" }}>Connecting to session…</div>
        </div>
      </div>
    );
  }

  if (!joined) {
    return (
      <div style={{ height: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "#1a1a1a" }}>
        <div style={{
          background: "#242424",
          border: "1px solid #333",
          borderRadius: 12,
          padding: "40px 48px",
          textAlign: "center",
          maxWidth: 400,
          width: "100%",
          boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
        }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>📹</div>
          <h2 style={{ color: "#fff", fontWeight: 700, marginBottom: 8, fontSize: 22 }}>
            Ready to join?
          </h2>
          <p style={{ color: "#aaa", fontSize: 14, marginBottom: 8 }}>
            Session: <span style={{ color: "#ddd", fontWeight: 500 }}>{roomName}</span>
          </p>
          <p style={{ color: "#888", fontSize: 13, marginBottom: 28, lineHeight: 1.5 }}>
            Your browser will ask permission to use your camera and microphone. Please click <strong style={{ color: "#aaa" }}>Allow</strong> when prompted.
          </p>
          <div style={{ display: "flex", gap: 12, justifyContent: "center", marginBottom: 16 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#aaa", fontSize: 13 }}>
              <span style={{ fontSize: 18 }}>🎤</span> Microphone
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, color: "#aaa", fontSize: 13 }}>
              <span style={{ fontSize: 18 }}>📷</span> Camera
            </div>
          </div>
          <button
            className="btn btn-primary w-100"
            style={{ padding: "10px 0", fontWeight: 600, fontSize: 15 }}
            onClick={() => setJoined(true)}
          >
            Join Session
          </button>
          <button
            className="btn btn-link w-100 mt-2"
            style={{ color: "#666", fontSize: 13 }}
            onClick={() => navigate(-1)}
          >
            Go back
          </button>
        </div>
      </div>
    );
  }

  const activePanels = [showVideo, showWhiteboard, showQuestion].filter(Boolean).length;
  const colClass = activePanels === 1 ? "col-12" : activePanels === 2 ? "col-6" : "col-4";

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#1a1a1a" }}>
      {/* Toolbar */}
      <div
        className="d-flex align-items-center gap-2 px-3"
        style={{ flexShrink: 0, height: 48, background: "#111", color: "#fff" }}
      >
        <span style={{ fontWeight: 600, marginRight: 8 }}>
          {roomName}
        </span>
        <button
          className={`btn btn-sm ${showVideo ? "btn-light" : "btn-outline-secondary"}`}
          onClick={() => setShowVideo((v: boolean) => { pref.set("chat_show_video", !v); return !v; })}
        >
          Video
        </button>
        <button
          className={`btn btn-sm ${showWhiteboard ? "btn-light" : "btn-outline-secondary"}`}
          onClick={() => setShowWhiteboard((v: boolean) => { pref.set("chat_show_whiteboard", !v); return !v; })}
        >
          Whiteboard
        </button>
        <button
          className={`btn btn-sm ${showQuestion ? "btn-light" : "btn-outline-secondary"}`}
          onClick={() => setShowQuestion((v: boolean) => { pref.set("chat_show_question", !v); return !v; })}
        >
          Question
        </button>
        <button
          className="btn btn-sm btn-danger ms-auto"
          onClick={async () => {
            if (isTutor && roomName) {
              await apiFetch("/api/sessions/end_session/", {
                method: "POST",
                body: JSON.stringify({ room_name: roomName }),
              }).catch(() => {});
              const tutorId = roomMatch?.[1];
              if (tutorId) {
                navigate(`/tutors/${tutorId}/post-tuition`);
                return;
              }
            }
            navigate(-1);
          }}
        >
          Leave
        </button>
      </div>

      {/* Panels */}
      <LKRoom
        token={token}
        serverUrl={livekitUrl}
        connect={true}
        audio={true}
        video={true}
        style={{ flex: 1, overflow: "hidden" }}
      >
        <RoomAudioRenderer />
        <div className="row g-0" style={{ height: "100%" }}>
          {showVideo && (
            <div className={colClass} style={{ height: "100%", borderRight: "1px solid #333" }}>
              <VideoPanel />
            </div>
          )}
          {showWhiteboard && (
            <div className={colClass} style={{ height: "100%", borderRight: "1px solid #333" }}>
              <WhiteboardPanel />
            </div>
          )}
          {showQuestion && (
            <div className={colClass} style={{ height: "100%", overflow: "hidden", background: "#fff" }}>
              <QuestionPanel isTutor={isTutor} roomName={roomName!} studentId={studentId} />
            </div>
          )}
          {activePanels === 0 && (
            <div className="col-12 d-flex align-items-center justify-content-center text-white">
              All panels hidden. Use the toolbar to show panels.
            </div>
          )}
        </div>
      </LKRoom>
    </div>
  );
}
