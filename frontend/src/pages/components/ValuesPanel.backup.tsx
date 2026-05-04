interface ValuesPanelProps {
  substitutedYaml: string | null;
  diagramCode: string | null;
  backendSvg: string | null;
}


export function ValuesPanel({
  substitutedYaml,
  diagramCode,
  backendSvg,
}: ValuesPanelProps) {

return (
  <div
    style={{
      whiteSpace: "pre-wrap",
      fontFamily: "monospace",
      fontSize: "0.85rem",
    }}
  >
    <pre>{typeof substitutedYaml === "string"
      ? substitutedYaml
      : JSON.stringify(substitutedYaml, null, 2)
    }</pre>

    <pre>{backendSvg ?? "[none]"}</pre>
  </div>
);

}
