import { useState } from "react";

type Op = "+" | "-" | "×" | "÷" | null;

export function Calculator({ onClose }: { onClose?: () => void } = {}) {
  const [display, setDisplay] = useState("0");
  const [prevValue, setPrevValue] = useState<number | null>(null);
  const [operator, setOperator] = useState<Op>(null);
  const [waitingForNew, setWaitingForNew] = useState(false);

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
      case "÷": return b !== 0 ? a / b : 0;
      default:  return b;
    }
  }

  function clean(n: number): string {
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

  function pressSquare() {
    const n = parseFloat(display);
    setDisplay(clean(n * n));
    setWaitingForNew(true);
  }

  function pressSqrt() {
    const n = parseFloat(display);
    setDisplay(n < 0 ? "Error" : clean(Math.sqrt(n)));
    setWaitingForNew(true);
  }

  function pressPi() {
    setDisplay(clean(Math.PI));
    setWaitingForNew(false);
  }

  const isActiveOp = (op: Op) => operator === op && waitingForNew;

  const btn = (
    label: string,
    onClick: () => void,
    opts: { wide?: boolean; color?: string; text?: string } = {}
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
        fontSize: 20,
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

  const opColor = (op: Op) =>
    isActiveOp(op) ? "#fff" : "#ff9f0a";
  const opText = (op: Op) =>
    isActiveOp(op) ? "#ff9f0a" : "#fff";

  return (
    <div style={{
      background: "#1c1c1e",
      borderRadius: onClose ? "0 0 16px 16px" : 16,
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
            top: 8,
            right: 8,
            background: "none",
            border: "none",
            color: "#888",
            fontSize: 18,
            lineHeight: 1,
            cursor: "pointer",
            padding: "0 4px",
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

      {/* Button grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
        {btn("x²",  pressSquare, { color: "#3a3a3c" })}
        {btn("√x",  pressSqrt,   { color: "#3a3a3c" })}
        {btn("π",   pressPi,     { color: "#3a3a3c" })}
        <div />

        {btn("AC",  pressClear,    { color: "#a5a5a5", text: "#000" })}
        {btn("+/−", pressNegate,   { color: "#a5a5a5", text: "#000" })}
        {btn("%",   pressPercent,  { color: "#a5a5a5", text: "#000" })}
        {btn("÷",   () => pressOperator("÷"), { color: opColor("÷"), text: opText("÷") })}

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
