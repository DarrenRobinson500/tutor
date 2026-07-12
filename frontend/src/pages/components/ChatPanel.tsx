import { Chat } from "@livekit/components-react";

// Cast to any to handle React 19 / @livekit/components-react type incompatibility
const LKChat = Chat as React.ComponentType<any>;

export function ChatPanel() {
  return (
    <div
      data-lk-theme="default"
      style={{ height: "100%", overflow: "hidden", background: "#1a1a1a" }}
    >
      <LKChat style={{ height: "100%" }} />
    </div>
  );
}
