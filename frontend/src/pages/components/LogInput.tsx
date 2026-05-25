import { useRef, useEffect } from "react";

interface LogInputProps {
  base: string;
  arg: string;
  onBaseChange: (v: string) => void;
  onArgChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  autoFocus?: boolean;
}

export function LogInput({ base, arg, onBaseChange, onArgChange, onSubmit, disabled, autoFocus }: LogInputProps) {
  const baseRef = useRef<HTMLInputElement>(null);
  const argRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!autoFocus) return;
    const t = setTimeout(() => baseRef.current?.focus(), 50);
    return () => clearTimeout(t);
  }, [autoFocus]);

  return (
    <div style={{ display: "inline-flex", alignItems: "flex-end", gap: 1 }}>
      <span style={{ fontSize: 22, lineHeight: 1.3 }}>log</span>
      {/* Base subscript input */}
      <input
        ref={baseRef}
        type="text"
        inputMode="decimal"
        value={base}
        onChange={e => onBaseChange(e.target.value)}
        onKeyDown={e => {
          if (e.key === "Enter" || e.key === "(" || e.key === "ArrowRight") {
            e.preventDefault();
            argRef.current?.focus();
          }
        }}
        disabled={disabled}
        placeholder="2"
        style={{
          width: 36,
          fontSize: 13,
          verticalAlign: "sub",
          textAlign: "center",
          backgroundColor: disabled ? "#f8f9fa" : "#fff9c4",
          border: "1px solid #adb5bd",
          borderRadius: 4,
          padding: "2px 3px",
          marginBottom: 3,
        }}
      />
      <span style={{ fontSize: 22, lineHeight: 1.3 }}>(</span>
      {/* Argument input */}
      <input
        ref={argRef}
        type="text"
        inputMode="decimal"
        value={arg}
        onChange={e => onArgChange(e.target.value)}
        onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); onSubmit(); } }}
        disabled={disabled}
        placeholder="x"
        style={{
          width: 60,
          fontSize: 18,
          textAlign: "center",
          backgroundColor: disabled ? "#f8f9fa" : "#fff9c4",
          border: "1px solid #adb5bd",
          borderRadius: 4,
          padding: "2px 8px",
        }}
      />
      <span style={{ fontSize: 22, lineHeight: 1.3 }}>)</span>
    </div>
  );
}
