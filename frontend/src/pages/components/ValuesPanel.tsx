import React from "react";

interface ValuesPanelProps {
  substitutedYaml: string | null;
  diagramCode: string | null;
  backendSvg: string | null;
}

const TOP_LEVEL_KEY = /^([a-zA-Z_][a-zA-Z0-9_]*\s*:)(.*)/;

function renderYaml(text: string) {
  const lines = text.split("\n");
  const elements: React.ReactNode[] = [];
  let firstHeading = true;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const m = !line.startsWith(" ") && !line.startsWith("\t") && TOP_LEVEL_KEY.exec(line);

    if (m) {
      if (!firstHeading) {
        elements.push(<br key={`gap-${i}`} />);
      }
      elements.push(
        <span key={i}>
          <span style={{ fontWeight: "bold" }}>{m[1]}</span>{m[2]}{"\n"}
        </span>
      );
      firstHeading = false;
    } else {
      elements.push(<span key={i}>{line}{"\n"}</span>);
    }
  }

  return elements;
}

export function ValuesPanel({
  substitutedYaml,
  diagramCode,
  backendSvg,
}: ValuesPanelProps) {
  const text = typeof substitutedYaml === "string"
    ? substitutedYaml
    : JSON.stringify(substitutedYaml, null, 2);

  return (
    <div
      style={{
        whiteSpace: "pre-wrap",
        fontFamily: "monospace",
        fontSize: "0.85rem",
      }}
    >
      <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "inherit", fontSize: "inherit", color: "inherit" }}>
        {text ? renderYaml(text) : null}
      </pre>
      {backendSvg && (
        <pre style={{ margin: 0, marginTop: "0.5rem" }}>{backendSvg}</pre>
      )}
    </div>
  );
}