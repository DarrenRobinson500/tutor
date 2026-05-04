import {
  useTracks,
  useLocalParticipant,
  VideoTrack,
} from "@livekit/components-react";
import { Track } from "livekit-client";

// Cast to any to handle React 19 / @livekit/components-react type incompatibility
const LKVideoTrack = VideoTrack as React.ComponentType<any>;

export function VideoPanel() {
  const { localParticipant, isMicrophoneEnabled, isCameraEnabled } =
    useLocalParticipant();

  const remoteTracks = useTracks([{ source: Track.Source.Camera, withPlaceholder: false }])
    .filter((t) => !t.participant.isLocal && t.publication != null);

  const localTracks = useTracks([{ source: Track.Source.Camera, withPlaceholder: false }])
    .filter((t) => t.participant.isLocal && t.publication != null);

  const toggleMic = () =>
    localParticipant.setMicrophoneEnabled(!isMicrophoneEnabled);

  const toggleCamera = () =>
    localParticipant.setCameraEnabled(!isCameraEnabled);

  return (
    <div
      style={{
        position: "relative",
        height: "100%",
        minHeight: 300,
        background: "#111",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        overflow: "hidden",
      }}
    >
      {/* Remote video — fills the panel */}
      {remoteTracks.length > 0 ? (
        remoteTracks.map((t) => (
          <LKVideoTrack
            key={t.publication!.trackSid}
            trackRef={t}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        ))
      ) : (
        <div className="text-white text-center p-4" style={{ opacity: 0.6 }}>
          <div style={{ fontSize: 48, marginBottom: 8 }}>👤</div>
          <div>Waiting for other participant…</div>
        </div>
      )}

      {/* Local video — picture-in-picture */}
      {localTracks.map((t) => (
        <div
          key={t.publication!.trackSid}
          style={{
            position: "absolute",
            bottom: 56,
            right: 10,
            width: 160,
            height: 90,
            borderRadius: 8,
            overflow: "hidden",
            border: "2px solid rgba(255,255,255,0.3)",
            background: "#222",
          }}
        >
          <LKVideoTrack
            trackRef={t}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </div>
      ))}

      {/* Controls */}
      <div
        style={{
          position: "absolute",
          bottom: 10,
          left: "50%",
          transform: "translateX(-50%)",
          display: "flex",
          gap: 8,
        }}
      >
        <button
          className={`btn btn-sm ${isMicrophoneEnabled ? "btn-light" : "btn-danger"}`}
          onClick={toggleMic}
          title={isMicrophoneEnabled ? "Mute" : "Unmute"}
        >
          {isMicrophoneEnabled ? "🎤" : "🔇"}
        </button>
        <button
          className={`btn btn-sm ${isCameraEnabled ? "btn-light" : "btn-danger"}`}
          onClick={toggleCamera}
          title={isCameraEnabled ? "Hide camera" : "Show camera"}
        >
          {isCameraEnabled ? "📹" : "📷"}
        </button>
      </div>
    </div>
  );
}
