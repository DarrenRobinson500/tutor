import { Chat } from "@livekit/components-react";

// Cast to any to handle React 19 / @livekit/components-react type incompatibility
const LKChat = Chat as React.ComponentType<any>;

export function ChatPanel() {
  return (
    <div
      data-lk-theme="default"
      className="chat-panel-light"
      style={{
        height: "100%",
        overflow: "hidden",
        background: "#fff",
        // Override LiveKit's dark theme variables so the panel matches the
        // white background of the other panels (Whiteboard/Question).
        "--lk-bg": "#fff",
        "--lk-bg2": "#fff",
        "--lk-bg3": "#f1f3f5",
        "--lk-bg5": "#e9ecef",
        "--lk-fg": "#1a1a1a",
        "--lk-fg5": "#6c757d",
        "--lk-border-color": "rgba(0,0,0,0.1)",
        "--lk-control-bg": "#f1f3f5",
      } as React.CSSProperties}
    >
      {/* Remote message bubbles keep the blue accent background — force white text for contrast */}
      <style>{`
        .chat-panel-light [data-lk-message-origin="remote"] .lk-message-body {
          color: #fff;
        }
      `}</style>
      <LKChat style={{ height: "100%" }} />
    </div>
  );
}
