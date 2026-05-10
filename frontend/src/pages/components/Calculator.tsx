import { useState, useRef, useEffect } from "react";

type Op = "+" | "-" | "×" | "÷" | "^" | null;

export function Calculator({ onClose }: { onClose?: () => void } = {}) {
  const [display, setDisplay]           = useState("0");
  const [prevValue, setPrevValue]       = useState<number | null>(null);
  const [operator, setOperator]         = useState<Op>(null);
  const [waitingForNew, setWaitingForNew] = useState(false);
  const [showSci, setShowSci]           = useState(false);

  function inputDigit(d: string) {
    if (waitingForNew) {
      setDisplay(d);
      setWaitingForNew(false);
    } else {
      setDisplay(prev => prev === "0" ? d : prev.length < 12 ? prev + d : prev);
    }
  }

  function inputDecimal() {
    if (waitingForNew) { setDisplay("0."); setWaitingForNew(false); return; }
    if (!display.includes(".")) setDisplay(prev => prev + ".");
  }

  function compute(a: number, b: number, op: Op): number {
    switch (op) {
      case "+": return a + b;
      case "-": return a - b;
      case "×": return a * b;
      case "÷": return b !== 0 ? a / b : NaN;
      case "^": return Math.pow(a, b);
      default:  return b;
    }
  }

  function clean(n: number): string {
    if (!isFinite(n)) return "Error";
    const r = Math.round(n * 1e9) / 1e9;
    return String(r);
  }

  function pressOperator(op: Op) {
    const cur = parseFloat(display);
    if (prevValue !== null && operator && !waitingForNew) {
      const result = compute(prevValue, cur, operator);
      setDisplay(clean(result));
      setPrevValue(result);
    } else {
      setPrevValue(cur);
    }
    setOperator(op);
    setWaitingForNew(true);
  }

  function pressEquals() {
    if (prevValue === null || !operator) return;
    const result = compute(prevValue, parseFloat(display), operator);
    setDisplay(clean(result));
    setPrevValue(null);
    setOperator(null);
    setWaitingForNew(true);
  }

  function pressClear() {
    setDisplay("0");
    setPrevValue(null);
    setOperator(null);
    setWaitingForNew(false);
  }

  function pressBackspace() {
    if (waitingForNew) return;
    setDisplay(prev => prev.length > 1 ? prev.slice(0, -1) : "0");
  }

  function pressNegate() {
    setDisplay(prev => {
      const n = parseFloat(prev);
      return n === 0 ? "0" : clean(-n);
    });
  }

  function pressPercent() {
    setDisplay(prev => clean(parseFloat(prev) / 100));
    setWaitingForNew(false);
  }

  // ── Scientific / unary functions ─────────────────────────────────────────────

  function pressSquare()  { setDisplay(clean(Math.pow(parseFloat(display), 2)));  setWaitingForNew(true); }
  function pressSqrt()    { const n = parseFloat(display); setDisplay(n < 0 ? "Error" : clean(Math.sqrt(n))); setWaitingForNew(true); }
  function pressPi()      { setDisplay(clean(Math.PI)); setWaitingForNew(false); }
  function pressE()       { setDisplay(clean(Math.E));  setWaitingForNew(false); }

  function pressSin()  { setDisplay(clean(Math.sin(parseFloat(display) * Math.PI / 180))); setWaitingForNew(true); }
  function pressCos()  { setDisplay(clean(Math.cos(parseFloat(display) * Math.PI / 180))); setWaitingForNew(true); }
  function pressTan()  { const r = Math.tan(parseFloat(display) * Math.PI / 180); setDisplay(Math.abs(r) > 1e10 ? "Error" : clean(r)); setWaitingForNew(true); }
  function pressAsin() { const n = parseFloat(display); setDisplay(n < -1 || n > 1 ? "Error" : clean(Math.asin(n) * 180 / Math.PI)); setWaitingForNew(true); }
  function pressAcos() { const n = parseFloat(display); setDisplay(n < -1 || n > 1 ? "Error" : clean(Math.acos(n) * 180 / Math.PI)); setWaitingForNew(true); }
  function pressAtan() { setDisplay(clean(Math.atan(parseFloat(display)) * 180 / Math.PI)); setWaitingForNew(true); }

  function pressLog()    { const n = parseFloat(display); setDisplay(n <= 0 ? "Error" : clean(Math.log10(n))); setWaitingForNew(true); }
  function pressLn()     { const n = parseFloat(display); setDisplay(n <= 0 ? "Error" : clean(Math.log(n)));   setWaitingForNew(true); }
  function pressExpX()   { setDisplay(clean(Math.exp(parseFloat(display)))); setWaitingForNew(true); }
  function pressTenPow() { setDisplay(clean(Math.pow(10, parseFloat(display)))); setWaitingForNew(true); }

  // ── Physical keyboard support ────────────────────────────────────────────────

  const keyHandlerRef = useRef<(e: KeyboardEvent) => void>(() => {});
  keyHandlerRef.current = (e: KeyboardEvent) => {
    const tag = (document.activeElement as HTMLElement)?.tagName?.toLowerCase();
    if (tag === "input" || tag === "textarea") return;
    switch (e.key) {
      case "0": case "1": case "2": case "3": case "4":
      case "5": case "6": case "7": case "8": case "9":
        e.preventDefault(); inputDigit(e.key); break;
      case ".": e.preventDefault(); inputDecimal(); break;
      case "+": e.preventDefault(); pressOperator("+"); break;
      case "-": e.preventDefault(); pressOperator("-"); break;
      case "*": e.preventDefault(); pressOperator("×"); break;
      case "/": e.preventDefault(); pressOperator("÷"); break;
      case "^": e.preventDefault(); pressOperator("^"); break;
      case "Enter": case "=": e.preventDefault(); pressEquals(); break;
      case "Backspace": case "Delete": e.preventDefault(); pressBackspace(); break;
      case "Escape": e.preventDefault(); pressClear(); break;
      case "%": e.preventDefault(); pressPercent(); break;
    }
  };
  useEffect(() => {
    function listener(e: KeyboardEvent) { keyHandlerRef.current(e); }
    document.addEventListener("keydown", listener);
    return () => document.removeEventListener("keydown", listener);
  }, []);

  // ── Styling helpers ──────────────────────────────────────────────────────────

  const isActiveOp = (op: Op) => operator === op && waitingForNew;
  const opColor    = (op: Op) => isActiveOp(op) ? "#fff"    : "#ff9f0a";
  const opText     = (op: Op) => isActiveOp(op) ? "#ff9f0a" : "#fff";

  const btn = (
    label: string,
    onClick: () => void,
    opts: { wide?: boolean; color?: string; text?: string; fontSize?: number } = {}
  ) => (
    <button
      key={label}
      onClick={onClick}
      style={{
        gridColumn: opts.wide ? "span 2" : undefined,
        background: opts.color ?? "#505050",
        color: opts.text ?? "#fff",
        border: "none",
        borderRadius: 8,
        fontSize: opts.fontSize ?? 20,
        fontWeight: 500,
        padding: "14px 0",
        cursor: "pointer",
        transition: "filter 0.1s",
      }}
      onMouseDown={e => (e.currentTarget.style.filter = "brightness(1.3)")}
      onMouseUp={e => (e.currentTarget.style.filter = "")}
      onMouseLeave={e => (e.currentTarget.style.filter = "")}
    >
      {label}
    </button>
  );

  const sciBtn = (label: string, onClick: () => void) => (
    <button
      key={label}
      onClick={onClick}
      style={{
        background: "#3a3a3c",
        color: "#fff",
        border: "none",
        borderRadius: 8,
        fontSize: 13,
        fontWeight: 500,
        padding: "10px 0",
        cursor: "pointer",
        transition: "filter 0.1s",
      }}
      onMouseDown={e => (e.currentTarget.style.filter = "brightness(1.3)")}
      onMouseUp={e => (e.currentTarget.style.filter = "")}
      onMouseLeave={e => (e.currentTarget.style.filter = "")}
    >
      {label}
    </button>
  );

  return (
    <div style={{
      background: "#1c1c1e",
      borderRadius: "0 0 16px 16px",
      padding: 12,
      userSelect: "none",
      boxShadow: "0 4px 24px rgba(0,0,0,0.25)",
      position: "relative",
    }}>
      {onClose && (
        <button
          onClick={onClose}
          style={{
            position: "absolute",
            top: 8, right: 8,
            background: "none", border: "none",
            color: "#888", fontSize: 18, lineHeight: 1,
            cursor: "pointer", padding: "0 4px",
          }}
          aria-label="Close calculator"
        >
          ×
        </button>
      )}

      {/* Display */}
      <div style={{
        background: "#000",
        borderRadius: 10,
        padding: "10px 14px",
        marginBottom: 10,
        minHeight: 56,
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "flex-end",
      }}>
        <span style={{
          color: "#fff",
          fontSize: display.length > 9 ? 20 : 32,
          fontWeight: 300,
          letterSpacing: -0.5,
          wordBreak: "break-all",
          textAlign: "right",
        }}>
          {display}
        </span>
      </div>

      {/* Scientific panel */}
      {showSci && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 8 }}>
          {sciBtn("sin",    pressSin)}
          {sciBtn("cos",    pressCos)}
          {sciBtn("tan",    pressTan)}
          {sciBtn("π",      pressPi)}
          {sciBtn("sin⁻¹",  pressAsin)}
          {sciBtn("cos⁻¹",  pressAcos)}
          {sciBtn("tan⁻¹",  pressAtan)}
          {sciBtn("e",      pressE)}
          {sciBtn("log",    pressLog)}
          {sciBtn("ln",     pressLn)}
          {sciBtn("10ˣ",    pressTenPow)}
          {sciBtn("eˣ",     pressExpX)}
        </div>
      )}

      {/* Main grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>

        {/* Scientific row */}
        {btn("xʸ",  () => pressOperator("^"), { color: isActiveOp("^") ? "#fff" : "#3a3a3c", text: isActiveOp("^") ? "#ff9f0a" : "#fff", fontSize: 18 })}
        {btn("x²",  pressSquare,              { color: "#3a3a3c" })}
        {btn("√x",  pressSqrt,               { color: "#3a3a3c" })}
        {btn("Sci", () => setShowSci(v => !v), { color: showSci ? "#0a84ff" : "#3a3a3c", fontSize: 16 })}

        {/* Utility row */}
        {btn("AC",  pressClear,   { color: "#a5a5a5", text: "#000" })}
        {btn("+/−", pressNegate,  { color: "#a5a5a5", text: "#000" })}
        {btn("%",   pressPercent, { color: "#a5a5a5", text: "#000" })}
        {btn("÷",   () => pressOperator("÷"), { color: opColor("÷"), text: opText("÷") })}

        {/* Digit rows */}
        {btn("7", () => inputDigit("7"))}
        {btn("8", () => inputDigit("8"))}
        {btn("9", () => inputDigit("9"))}
        {btn("×", () => pressOperator("×"), { color: opColor("×"), text: opText("×") })}

        {btn("4", () => inputDigit("4"))}
        {btn("5", () => inputDigit("5"))}
        {btn("6", () => inputDigit("6"))}
        {btn("−", () => pressOperator("-"), { color: opColor("-"), text: opText("-") })}

        {btn("1", () => inputDigit("1"))}
        {btn("2", () => inputDigit("2"))}
        {btn("3", () => inputDigit("3"))}
        {btn("+", () => pressOperator("+"), { color: opColor("+"), text: opText("+") })}

        {btn("⌫",  pressBackspace, { color: "#505050" })}
        {btn("0",  () => inputDigit("0"))}
        {btn(".",  inputDecimal)}
        {btn("=",  pressEquals,   { color: "#ff9f0a" })}
      </div>
    </div>
  );
}

export function DraggableCalculator({ onClose }: { onClose: () => void }) {
  const [pos, setPos] = useState({ x: window.innerWidth - 310, y: 80 });
  const dragRef = useRef<{ startX: number; startY: number; origX: number; origY: number } | null>(null);

  function onDragStart(e: React.MouseEvent) {
    e.preventDefault();
    dragRef.current = { startX: e.clientX, startY: e.clientY, origX: pos.x, origY: pos.y };
    function onMove(ev: MouseEvent) {
      if (!dragRef.current) return;
      setPos({
        x: dragRef.current.origX + (ev.clientX - dragRef.current.startX),
        y: dragRef.current.origY + (ev.clientY - dragRef.current.startY),
      });
    }
    function onUp() {
      dragRef.current = null;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }

  return (
    <div style={{ position: "fixed", left: pos.x, top: pos.y, zIndex: 1000, width: 286, transform: "scale(0.82)", transformOrigin: "top left" }}>
      <div
        onMouseDown={onDragStart}
        style={{
          height: 28,
          background: "#3a3a3c",
          borderRadius: "12px 12px 0 0",
          cursor: "grab",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
        }}
      >
        <div style={{ width: 40, height: 4, borderRadius: 2, background: "#888" }} />
        <button
          onMouseDown={e => e.stopPropagation()}
          onClick={onClose}
          style={{
            position: "absolute",
            right: 8,
            background: "none",
            border: "none",
            color: "#aaa",
            fontSize: 18,
            lineHeight: 1,
            cursor: "pointer",
            padding: "0 4px",
          }}
          aria-label="Close calculator"
        >
          ×
        </button>
      </div>
      <Calculator />
    </div>
  );
}
