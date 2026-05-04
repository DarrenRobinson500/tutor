interface LogsPanelProps {
  validation: any; // you can tighten this later
  preview: any;    // same here
}

function safeStringify(value: any) {
  try {
    return JSON.stringify(value, getCircularReplacer(), 2);
  } catch (err) {
    return `<< Unserializable object >>`;
  }
}

function getCircularReplacer() {
  const seen = new WeakSet();
  return (key: string, value: any) => {
    if (typeof value === "object" && value !== null) {
      if (seen.has(value)) {
        return "<< circular >>";
      }
      seen.add(value);
    }
    return value;
  };
}


export function LogsPanel({ validation, preview }: LogsPanelProps) {

// console.log("LogsPanel props:", { validation, preview });



  return (
    <div
      style={{
        borderTop: "1px solid #ddd",
        padding: 12,
        background: "#f7f7f7",
        height: 150,
        overflow: "auto",
      }}
    >
      <h4>Logs</h4>

    {validation && (
      <>
        <strong>Validation:</strong>
        <pre>{safeStringify(validation)}</pre>
      </>
    )}

    {preview && (
      <>
        <strong>Preview:</strong>
        <pre>{safeStringify(preview)}</pre>
      </>
    )}

    </div>
  );
}