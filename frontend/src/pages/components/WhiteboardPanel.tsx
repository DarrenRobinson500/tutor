import { useEffect, useRef, useState } from "react";
import { useRoomContext } from "@livekit/components-react";
import { RoomEvent } from "livekit-client";

const TOPIC = "whiteboard";

interface StrokeEvent {
  topic: string;
  type: "start" | "draw" | "end" | "clear";
  x: number;
  y: number;
  color: string;
  width: number;
}

export function WhiteboardPanel() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isDrawing = useRef(false);
  const lastPos = useRef<{ x: number; y: number } | null>(null);
  const room = useRoomContext();

  const [color, setColor] = useState("#1a1a1a");
  const [lineWidth, setLineWidth] = useState(3);
  const [isEraser, setIsEraser] = useState(false);

  const activeColor = isEraser ? "#ffffff" : color;
  const activeWidth = isEraser ? 20 : lineWidth;

  // Handle incoming drawing events from remote participant
  useEffect(() => {
    const handleData = (
      payload: Uint8Array,
      _participant: any,
      _kind: any,
      topic?: string
    ) => {
      if (topic !== TOPIC) return;
      try {
        const event: StrokeEvent = JSON.parse(
          new TextDecoder().decode(payload)
        );
        applyEvent(event);
      } catch {}
    };

    room.on(RoomEvent.DataReceived, handleData);
    return () => {
      room.off(RoomEvent.DataReceived, handleData);
    };
  }, [room]);

  const publish = (event: Omit<StrokeEvent, "topic">) => {
    const data = new TextEncoder().encode(
      JSON.stringify({ topic: TOPIC, ...event })
    );
    room.localParticipant.publishData(data, { reliable: true, topic: TOPIC });
  };

  const getCtx = () => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    return { canvas, ctx };
  };

  const applyEvent = (event: StrokeEvent) => {
    const res = getCtx();
    if (!res) return;
    const { canvas, ctx } = res;

    if (event.type === "clear") {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      return;
    }

    ctx.strokeStyle = event.color;
    ctx.lineWidth = event.width;

    if (event.type === "start") {
      ctx.beginPath();
      ctx.moveTo(event.x, event.y);
    } else if (event.type === "draw") {
      ctx.lineTo(event.x, event.y);
      ctx.stroke();
    }
  };

  const getPos = (
    e: React.MouseEvent | React.TouchEvent
  ): { x: number; y: number } => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    if ("touches" in e) {
      const touch = e.touches[0];
      return {
        x: (touch.clientX - rect.left) * scaleX,
        y: (touch.clientY - rect.top) * scaleY,
      };
    }
    return {
      x: (e.clientX - rect.left) * scaleX,
      y: (e.clientY - rect.top) * scaleY,
    };
  };

  const startDraw = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    isDrawing.current = true;
    const pos = getPos(e);
    lastPos.current = pos;

    const evt = { type: "start" as const, ...pos, color: activeColor, width: activeWidth };
    applyEvent({ topic: TOPIC, ...evt });
    publish(evt);
  };

  const draw = (e: React.MouseEvent | React.TouchEvent) => {
    e.preventDefault();
    if (!isDrawing.current) return;
    const pos = getPos(e);

    const evt = { type: "draw" as const, ...pos, color: activeColor, width: activeWidth };
    applyEvent({ topic: TOPIC, ...evt });
    publish(evt);
    lastPos.current = pos;
  };

  const endDraw = () => {
    isDrawing.current = false;
    lastPos.current = null;
  };

  const clearCanvas = () => {
    const res = getCtx();
    if (!res) return;
    res.ctx.clearRect(0, 0, res.canvas.width, res.canvas.height);
    publish({ type: "clear", x: 0, y: 0, color: "", width: 0 });
  };

  // Resize canvas to match container
  useEffect(() => {
    const resize = () => {
      const container = containerRef.current;
      const canvas = canvasRef.current;
      if (!container || !canvas) return;
      // Preserve drawing by copying to temp
      const temp = document.createElement("canvas");
      temp.width = canvas.width;
      temp.height = canvas.height;
      temp.getContext("2d")?.drawImage(canvas, 0, 0);
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
      canvas.getContext("2d")?.drawImage(temp, 0, 0);
    };
    resize();
    const observer = new ResizeObserver(resize);
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const COLORS = [
    "#1a1a1a", "#e74c3c", "#3498db", "#2ecc71",
    "#f39c12", "#9b59b6", "#1abc9c", "#ffffff",
  ];

  return (
    <div
      ref={containerRef}
      style={{
        height: "100%",
        minHeight: 300,
        display: "flex",
        flexDirection: "column",
        background: "#fff",
        position: "relative",
      }}
    >
      {/* Toolbar */}
      <div
        className="d-flex align-items-center gap-2 px-2 py-1 border-bottom"
        style={{ flexShrink: 0, background: "#f8f9fa", flexWrap: "wrap" }}
      >
        {COLORS.map((c) => (
          <button
            key={c}
            onClick={() => { setColor(c); setIsEraser(false); }}
            style={{
              width: 22,
              height: 22,
              borderRadius: "50%",
              background: c,
              border: color === c && !isEraser ? "3px solid #333" : "1px solid #ccc",
              cursor: "pointer",
              padding: 0,
              flexShrink: 0,
            }}
          />
        ))}
        <select
          className="form-select form-select-sm"
          style={{ width: 70 }}
          value={lineWidth}
          onChange={(e) => { setLineWidth(Number(e.target.value)); setIsEraser(false); }}
        >
          <option value={2}>Thin</option>
          <option value={4}>Medium</option>
          <option value={8}>Thick</option>
        </select>
        <button
          className={`btn btn-sm ${isEraser ? "btn-warning" : "btn-outline-secondary"}`}
          onClick={() => setIsEraser((v) => !v)}
          title="Eraser"
        >
          🧹
        </button>
        <button
          className="btn btn-sm btn-outline-danger ms-auto"
          onClick={clearCanvas}
          title="Clear whiteboard"
        >
          Clear
        </button>
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        style={{ flex: 1, cursor: isEraser ? "cell" : "crosshair", touchAction: "none" }}
        onMouseDown={startDraw}
        onMouseMove={draw}
        onMouseUp={endDraw}
        onMouseLeave={endDraw}
        onTouchStart={startDraw}
        onTouchMove={draw}
        onTouchEnd={endDraw}
      />
    </div>
  );
}
