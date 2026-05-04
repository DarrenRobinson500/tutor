import React, { useState, useEffect } from "react";

interface DiagramEditorProps {
  svg: string;
  onChange: (value: string) => void;
}

export function DiagramEditor({ svg, onChange }: DiagramEditorProps) {
  const [localSvg, setLocalSvg] = useState(svg);

  useEffect(() => {
    setLocalSvg(svg);
  }, [svg]);

  return (
    <div className="h-100 d-flex flex-column">
      <div className="mb-2 fw-bold">Diagram</div>
      <textarea
        className="form-control"
        style={{
          height: "100%",
          resize: "none",
          overflow: "auto",
          fontFamily: "monospace",
        }}
        value={localSvg}
        onChange={(e) => {
          const newValue = e.target.value;
          setLocalSvg(newValue);
          onChange(newValue);
        }}
      />
    </div>
  );
}