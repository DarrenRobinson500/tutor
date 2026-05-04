import { useState, useRef, useEffect } from "react";

interface PowerInputProps {
  value: string;                  // "x^-3", "1/x^3", or "x"
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  autoFocus?: boolean;
}

function parseValue(v: string): { frac: string; base: string; exp: string; isFrac: boolean } {
  if (v.includes("/")) {
    const slash = v.indexOf("/");
    const frac = v.slice(0, slash);
    const denom = v.slice(slash + 1);
    const caret = denom.indexOf("^");
    if (caret >= 0) {
      return { frac, base: denom.slice(0, caret), exp: denom.slice(caret + 1), isFrac: true };
    }
    return { frac, base: denom, exp: "", isFrac: true };
  }
  const caret = v.indexOf("^");
  if (caret >= 0) {
    return { frac: "", base: v.slice(0, caret), exp: v.slice(caret + 1), isFrac: false };
  }
  return { frac: "", base: v, exp: "", isFrac: false };
}

export function PowerInput({ value, onChange, onSubmit, disabled, autoFocus }: PowerInputProps) {
  const init = parseValue(value);
  const [frac, setFrac] = useState(init.frac);
  const [base, setBase] = useState(init.base);
  const [exp,  setExp]  = useState(init.exp);
  const [isFrac, setIsFrac] = useState(init.isFrac);
  const [mode, setMode] = useState<"base" | "exp">("base");
  const [focused, setFocused] = useState(false);
  const displayRef = useRef<HTMLDivElement>(null);
  const ownChangeRef = useRef(false);

  useEffect(() => {
    const p = parseValue(value);
    setFrac(p.frac); setBase(p.base); setExp(p.exp); setIsFrac(p.isFrac);
    // Only reset mode on external value changes, not ones we emitted ourselves.
    if (!ownChangeRef.current) setMode("base");
    ownChangeRef.current = false;
  }, [value]);

  useEffect(() => {
    if (!autoFocus) return;
    const timer = setTimeout(() => displayRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, [autoFocus]);

  function emit(f: string, b: string, e: string, fr: boolean) {
    let v: string;
    if (fr) {
      v = e ? `${f}/${b}^${e}` : b ? `${f}/${b}` : f;
    } else {
      v = e ? `${b}^${e}` : b;
    }
    ownChangeRef.current = true;
    onChange(v);
  }

  function handleKeyDown(ev: React.KeyboardEvent<HTMLDivElement>) {
    if (disabled) return;

    if (ev.key === "Enter") { ev.preventDefault(); onSubmit(); return; }

    // '/' enters fraction mode: what was typed as base becomes the numerator
    if (ev.key === "/" && !isFrac) {
      ev.preventDefault();
      setFrac(base); setBase(""); setIsFrac(true); setMode("base");
      emit(base, "", "", true);
      return;
    }

    if ((ev.key === "^" || ev.key === "ArrowUp") && mode !== "exp") {
      ev.preventDefault();
      setMode("exp");
      return;
    }

    if (ev.key === "Backspace") {
      ev.preventDefault();
      if (mode === "exp") {
        if (exp.length > 0) {
          const next = exp.slice(0, -1);
          setExp(next); emit(frac, base, next, isFrac);
        } else {
          setMode("base");
        }
      } else {
        if (base.length > 0) {
          const next = base.slice(0, -1);
          setBase(next); emit(frac, next, exp, isFrac);
        } else if (isFrac) {
          // Backspace past empty denominator: restore numerator to base, exit fraction mode
          setBase(frac); setFrac(""); setIsFrac(false);
          emit("", frac, exp, false);
        }
      }
      return;
    }

    const allowNeg = ev.key === "-" && mode === "exp" && exp === "";
    if (/^[A-Za-z0-9]$/.test(ev.key) || allowNeg) {
      ev.preventDefault();
      if (mode === "base") {
        const next = base + ev.key;
        setBase(next); emit(frac, next, exp, isFrac);
      } else {
        const next = exp + ev.key;
        setExp(next); emit(frac, base, next, isFrac);
      }
    }
  }

  const inExp  = mode === "exp";
  const showExp = inExp || exp.length > 0;

  const cursor = (
    <span
      style={{
        display: "inline-block",
        width: 2,
        background: "#333",
        marginLeft: 1,
        height: "0.85em",
        verticalAlign: "text-bottom",
        animation: focused ? "power-blink 1s step-end infinite" : "none",
      }}
    />
  );

  return (
    <>
      <style>{`
        @keyframes power-blink {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0; }
        }
      `}</style>

      <div style={{ display: "inline-flex", alignItems: "flex-end", gap: 6 }}>

        {/* ── Display box ── */}
        <div
          ref={displayRef}
          tabIndex={disabled ? undefined : 0}
          onKeyDown={handleKeyDown}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          style={{
            display: "inline-flex",
            alignItems: "baseline",
            border: `2px solid ${focused ? (inExp ? "#0d6efd" : "#333") : "#adb5bd"}`,
            borderRadius: 6,
            padding: "4px 12px",
            background: disabled ? "#f8f9fa" : "#fff9c4",
            fontSize: 22,
            cursor: disabled ? "default" : "text",
            minWidth: 64,
            outline: "none",
            userSelect: "none",
            lineHeight: 1.3,
          }}
        >
          {/* Numerator (fraction mode only) */}
          {isFrac && (
            <>
              <span style={{ color: "#000" }}>{frac || "?"}</span>
              <span style={{ padding: "0 6px", color: "#555", fontWeight: 300 }}>/</span>
            </>
          )}

          {/* Base (or denominator base) */}
          <span style={{ color: (!inExp && base === "") ? "#bbb" : "#000" }}>
            {base || (!inExp ? "?" : "")}
          </span>
          {!inExp && focused && cursor}

          {/* Exponent */}
          {showExp && (
            <span
              style={{
                fontSize: 14,
                position: "relative",
                top: "-0.6em",
                lineHeight: 1,
                color: exp === "" ? "#bbb" : "#000",
              }}
            >
              {exp || (inExp ? "?" : "")}
              {inExp && focused && cursor}
            </span>
          )}
        </div>

        {/* ── xⁿ mode button ── */}
        <button
          type="button"
          disabled={disabled}
          onMouseDown={ev => {
            ev.preventDefault();
            setMode("exp");
            displayRef.current?.focus();
          }}
          style={{
            fontSize: 14,
            padding: "4px 9px",
            border: `1px solid ${inExp && focused ? "#0d6efd" : "#999"}`,
            borderRadius: 4,
            background: inExp && focused ? "#e7f0ff" : "#f8f9fa",
            color: inExp && focused ? "#0d6efd" : "#555",
            fontWeight: inExp && focused ? 700 : 400,
            cursor: "pointer",
            transition: "all 0.1s",
          }}
          title="Enter exponent / power (or press ^)"
        >
          x<sup style={{ fontSize: 10 }}>n</sup>
        </button>

        {/* ── ½ fraction mode hint (only when not already in fraction mode) ── */}
        {!isFrac && (
          <span style={{ fontSize: 11, color: "#999", alignSelf: "center" }}>
            press / for fraction
          </span>
        )}

      </div>
    </>
  );
}
