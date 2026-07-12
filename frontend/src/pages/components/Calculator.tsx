import { useState, useRef, useEffect } from "react";

export function Calculator({ onClose }: { onClose?: () => void } = {}) {
  // Expression-based model: `expr` accumulates the expression string before
  // the number currently shown in `display`. On = we evaluate expr + display.
  const [display, setDisplay]         = useState("0");
  const [expr, setExpr]               = useState("");
  const [openParens, setOpenParens]   = useState(0);
  const [typing, setTyping]           = useState(false);
  const [showSci, setShowSci]         = useState(false);

  // ── Number entry ────────────────────────────────────────────────────────────

  function inputDigit(d: string) {
    if (typing) {
      setDisplay(prev => prev === "0" ? d : prev.length < 12 ? prev + d : prev);
    } else {
      setDisplay(d);
      setTyping(true);
    }
  }

  function inputDecimal() {
    if (!typing) { setDisplay("0."); setTyping(true); return; }
    if (!display.includes(".")) setDisplay(prev => prev + ".");
  }

  // ── Evaluation ──────────────────────────────────────────────────────────────

  function clean(n: number): string {
    if (!isFinite(n)) return "Error";
    const r = Math.round(n * 1e9) / 1e9;
    return String(r);
  }

  function evaluate(fullExpr: string): string {
    try {
      const js = fullExpr.replace(/×/g, "*").replace(/÷/g, "/").replace(/\^/g, "**");
      // eslint-disable-next-line no-new-func
      const result = Function('"use strict"; return (' + js + ')')() as number;
      return clean(result);
    } catch {
      return "Error";
    }
  }

  // ── Operators ───────────────────────────────────────────────────────────────

  function pressOperator(op: string) {
    // If no new number was typed since the last operator, just swap the operator
    if (!typing && /[+\-×÷^]$/.test(expr)) {
      setExpr(prev => prev.slice(0, -1) + op);
    } else {
      setExpr(prev => prev + display + op);
      setDisplay("0");
      setTyping(false);
    }
  }

  function pressOpenParen() {
    if (typing && display !== "0") {
      // Implicit multiplication: 5( → 5×(
      setExpr(prev => prev + display + "×(");
    } else {
      setExpr(prev => prev + "(");
    }
    setDisplay("0");
    setTyping(false);
    setOpenParens(prev => prev + 1);
  }

  function pressCloseParen() {
    if (openParens === 0) return;
    setExpr(prev => prev + display + ")");
    setDisplay("0");
    setTyping(false);
    setOpenParens(prev => prev - 1);
  }

  function pressEquals() {
    const fullExpr = expr + display;
    if (!fullExpr || fullExpr === "0") return;
    const closed = fullExpr + ")".repeat(openParens);
    const result = evaluate(closed);
    setDisplay(result);
    setExpr("");
    setOpenParens(0);
    setTyping(false);
  }

  // ── Utility ─────────────────────────────────────────────────────────────────

  function pressClear() {
    setDisplay("0");
    setExpr("");
    setOpenParens(0);
    setTyping(false);
  }

  function pressBackspace() {
    if (typing) {
      if (display.length > 1) {
        setDisplay(prev => prev.slice(0, -1));
      } else {
        setDisplay("0");
        setTyping(false);
      }
    } else if (expr.length > 0) {
      const last = expr[expr.length - 1];
      if (last === "(") setOpenParens(prev => Math.max(0, prev - 1));
      if (last === ")") setOpenParens(prev => prev + 1);
      setExpr(prev => prev.slice(0, -1));
    }
  }

  function pressNegate() {
    setDisplay(prev => {
      const n = parseFloat(prev);
      return n === 0 ? "0" : clean(-n);
    });
  }

  function pressPercent() {
    setDisplay(prev => clean(parseFloat(prev) / 100));
    setTyping(false);
  }

  // ── Scientific / unary ───────────────────────────────────────────────────────

  function applyUnary(fn: (n: number) => number | "Error") {
    const n = parseFloat(display);
    const r = fn(n);
    setDisplay(r === "Error" ? "Error" : clean(r as number));
    setTyping(false);
  }

  function pressSquare()  { applyUnary(n => Math.pow(n, 2)); }
  function pressSqrt()    { applyUnary(n => n < 0 ? "Error" : Math.sqrt(n)); }
  function pressPi()      { setDisplay(clean(Math.PI)); setTyping(false); }
  function pressE()       { setDisplay(clean(Math.E));  setTyping(false); }
  function pressSin()     { applyUnary(n => Math.sin(n * Math.PI / 180)); }
  function pressCos()     { applyUnary(n => Math.cos(n * Math.PI / 180)); }
  function pressTan()     { applyUnary(n => { const r = Math.tan(n * Math.PI / 180); return Math.abs(r) > 1e10 ? "Error" : r; }); }
  function pressAsin()    { applyUnary(n => n < -1 || n > 1 ? "Error" : Math.asin(n) * 180 / Math.PI); }
  function pressAcos()    { applyUnary(n => n < -1 || n > 1 ? "Error" : Math.acos(n) * 180 / Math.PI); }
  function pressAtan()    { applyUnary(n => Math.atan(n) * 180 / Math.PI); }
  function pressLog()     { applyUnary(n => n <= 0 ? "Error" : Math.log10(n)); }
  function pressLn()      { applyUnary(n => n <= 0 ? "Error" : Math.log(n)); }
  function pressExpX()    { applyUnary(n => Math.exp(n)); }
  function pressTenPow()  { applyUnary(n => Math.pow(10, n)); }

  // ── Keyboard support ─────────────────────────────────────────────────────────

  const keyHandlerRef = useRef<(e: KeyboardEvent) => void>(() => {});
  keyHandlerRef.current = (e: KeyboardEvent) => {
    const tag = (document.activeElement as HTMLElement)?.tagName?.toLowerCase();
    if (tag === "input" || tag === "textarea") return;
    switch (e.key) {
      case "0": case "1": case "2": case "3": case "4":
      case "5": case "6": case "7": case "8": case "9":
        e.preventDefault(); inputDigit(e.key); break;
      case ".":         e.preventDefault(); inputDecimal();         break;
      case "+":         e.preventDefault(); pressOperator("+");     break;
      case "-":         e.preventDefault(); pressOperator("-");     break;
      case "*":         e.preventDefault(); pressOperator("×");     break;
      case "/":         e.preventDefault(); pressOperator("÷");     break;
      case "^":         e.preventDefault(); pressOperator("^");     break;
      case "(":         e.preventDefault(); pressOpenParen();       break;
      case ")":         e.preventDefault(); pressCloseParen();      break;
      case "Enter": case "=": e.preventDefault(); pressEquals();    break;
      case "Backspace": case "Delete": e.preventDefault(); pressBackspace(); break;
      case "Escape":    e.preventDefault(); pressClear();           break;
      case "%":         e.preventDefault(); pressPercent();         break;
    }
  };
  useEffect(() => {
    function listener(e: KeyboardEvent) { keyHandlerRef.current(e); }
    document.addEventListener("keydown", listener);
    return () => document.removeEventListener("keydown", listener);
  }, []);

  // ── Styling helpers ──────────────────────────────────────────────────────────

  const isActiveOp = (op: string) => !typing && expr.endsWith(op);
  const opColor    = (op: string) => isActiveOp(op) ? "#fff"    : "#ff9f0a";
  const opText     = (op: string) => isActiveOp(op) ? "#ff9f0a" : "#fff";

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

  // Expression label: show pending expr with open-paren indicator
  const exprLabel = expr + (openParens > 0 ? " " + "·)".repeat(openParens) : "");

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
        padding: "8px 14px 10px",
        marginBottom: 10,
        minHeight: 64,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
        justifyContent: "flex-end",
      }}>
        {/* Pending expression context */}
        <span style={{
          color: "#666",
          fontSize: 12,
          minHeight: 16,
          wordBreak: "break-all",
          textAlign: "right",
          width: "100%",
        }}>
          {exprLabel}
        </span>
        {/* Current number */}
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
        {btn("xʸ", () => pressOperator("^"), { color: isActiveOp("^") ? "#fff" : "#3a3a3c", text: isActiveOp("^") ? "#ff9f0a" : "#fff", fontSize: 18 })}
        {btn("x²",  pressSquare,              { color: "#3a3a3c" })}
        {btn("√x",  pressSqrt,               { color: "#3a3a3c" })}
        {btn("Sci", () => setShowSci(v => !v), { color: showSci ? "#0a84ff" : "#3a3a3c", fontSize: 16 })}

        {/* Utility row */}
        {btn("AC", pressClear,               { color: "#a5a5a5", text: "#000" })}
        {btn("(",  pressOpenParen,           { color: "#a5a5a5", text: "#000", fontSize: 22 })}
        {btn(")",  pressCloseParen,          { color: "#a5a5a5", text: "#000", fontSize: 22 })}
        {btn("÷",  () => pressOperator("÷"), { color: opColor("÷"), text: opText("÷") })}

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
  const [pos, setPos] = useState({ x: window.innerWidth / 2 + 1.5 * (96 / 2.54) + Math.round(1.3 * 286 * 0.82), y: 140 });
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
