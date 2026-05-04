import { useState } from "react";

type ParamType = "integer" | "fraction" | "decimal" | "dollar" | "percent" | "choice";

interface Props {
  onInsert: (yaml: string) => void;
}

const TYPES: { id: ParamType; label: string }[] = [
  { id: "integer",  label: "Integer"  },
  { id: "fraction", label: "Fraction" },
  { id: "decimal",  label: "Decimal"  },
  { id: "dollar",   label: "Dollar"   },
  { id: "percent",  label: "Percent"  },
  { id: "choice",   label: "Choice"   },
];

export function ParameterHelper({ onInsert }: Props) {
  const [name,        setName]        = useState("n");
  const [type,        setType]        = useState<ParamType>("integer");

  // integer
  const [intMin,      setIntMin]      = useState(2);
  const [intMax,      setIntMax]      = useState(12);
  const [intSize,     setIntSize]     = useState("small");  // "none" | "small" | "medium" | "large"
  const [intSign,     setIntSign]     = useState("pos");    // "pos" | "neg" | "pos_neg"
  const [intBrackets, setIntBrackets] = useState(false);

  // fraction
  const [fracSize,    setFracSize]    = useState("small");
  const [fracProper,  setFracProper]  = useState("true");
  const [fracSign,    setFracSign]    = useState("pos");
  const [fracMixed,   setFracMixed]   = useState(false);

  // decimal
  const [decMin,      setDecMin]      = useState(1);
  const [decMax,      setDecMax]      = useState(10);
  const [decPlaces,   setDecPlaces]   = useState(1);

  // dollar
  const [dollarSize,  setDollarSize]  = useState("medium");

  // percent
  const [pctMin,      setPctMin]      = useState(10);
  const [pctMax,      setPctMax]      = useState(90);
  const [pctCommon,   setPctCommon]   = useState(false);

  // choice
  const [choiceVals,  setChoiceVals]  = useState("2, 3, 4, 5");

  function buildYaml(): string {
    const i2 = "  ", i4 = "    ";
    const lines: string[] = [`${i2}${name.trim() || "n"}:`];

    if (type === "integer") {
      if (intSize !== "none") {
        lines.push(`${i4}size: ${intSize}`);
      } else {
        lines.push(`${i4}min: ${intMin}`);
        lines.push(`${i4}max: ${intMax}`);
      }
      if (intSign !== "pos") lines.push(`${i4}sign: ${intSign}`);
      if (intBrackets) lines.push(`${i4}brackets_when_negative: true`);
    } else if (type === "fraction") {
      lines.push(`${i4}type: fraction`);
      lines.push(`${i4}size: ${fracSize}`);
      if (fracProper !== "omit") lines.push(`${i4}proper: ${fracProper}`);
      if (fracSign   !== "pos")  lines.push(`${i4}sign: ${fracSign}`);
      if (fracMixed)             lines.push(`${i4}mixed: true`);
    } else if (type === "decimal") {
      lines.push(`${i4}type: decimal`);
      lines.push(`${i4}min: ${decMin}`);
      lines.push(`${i4}max: ${decMax}`);
      lines.push(`${i4}decimal_places: ${decPlaces}`);
    } else if (type === "dollar") {
      lines.push(`${i4}type: dollar`);
      lines.push(`${i4}size: ${dollarSize}`);
    } else if (type === "percent") {
      lines.push(`${i4}type: percent`);
      if (pctCommon) {
        lines.push(`${i4}common: true`);
      } else {
        lines.push(`${i4}min: ${pctMin}`);
        lines.push(`${i4}max: ${pctMax}`);
      }
    } else if (type === "choice") {
      const vals = choiceVals.split(",").map(v => v.trim()).filter(Boolean);
      const parsed = vals.map(v => isNaN(Number(v)) ? `"${v}"` : v);
      lines.push(`${i4}type: choice`);
      lines.push(`${i4}values: [${parsed.join(", ")}]`);
    }

    return lines.join("\n");
  }

  const sel = (val: string, cur: string) =>
    `btn btn-sm ${val === cur ? "btn-primary" : "btn-outline-secondary"}`;

  return (
    <div style={{ padding: "8px 10px", background: "#1e1e1e", borderTop: "1px solid #333", color: "#ccc", fontSize: 12 }}>

      {/* Row 1: name + type */}
      <div className="d-flex align-items-center gap-2 flex-wrap mb-2">
        <span style={{ color: "#aaa", whiteSpace: "nowrap" }}>Name:</span>
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          style={{ width: 60, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }}
        />
        <span style={{ color: "#aaa", marginLeft: 4 }}>Type:</span>
        {TYPES.map(t => (
          <button key={t.id} className={sel(t.id, type)} style={{ fontSize: 11, padding: "1px 7px" }} onClick={() => setType(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Row 2: type-specific options */}
      <div className="d-flex align-items-center gap-2 flex-wrap mb-2">

        {type === "integer" && <>
          <span style={{ color: "#aaa" }}>Size:</span>
          {["none", "small", "medium", "large"].map(v => (
            <button key={v} className={sel(v, intSize)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setIntSize(v)}>{v}</button>
          ))}
          {intSize === "none" && <>
            <label style={{ color: "#aaa", marginLeft: 6 }}>Min:
              <input type="number" value={intMin} onChange={e => setIntMin(Number(e.target.value))}
                style={{ width: 50, marginLeft: 4, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }} />
            </label>
            <label style={{ color: "#aaa" }}>Max:
              <input type="number" value={intMax} onChange={e => setIntMax(Number(e.target.value))}
                style={{ width: 50, marginLeft: 4, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }} />
            </label>
          </>}
          <span style={{ color: "#aaa", marginLeft: 6 }}>Sign:</span>
          {["pos", "neg", "pos_neg"].map(v => (
            <button key={v} className={sel(v, intSign)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setIntSign(v)}>{v}</button>
          ))}
          <button className={`btn btn-sm ${intBrackets ? "btn-primary" : "btn-outline-secondary"}`} style={{ fontSize: 11, padding: "1px 6px", marginLeft: 6 }} onClick={() => setIntBrackets(b => !b)}>
            brackets_when_neg
          </button>
        </>}

        {type === "fraction" && <>
          <span style={{ color: "#aaa" }}>Size:</span>
          {["small","medium","large"].map(v => <button key={v} className={sel(v, fracSize)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setFracSize(v)}>{v}</button>)}
          <span style={{ color: "#aaa", marginLeft: 4 }}>Proper:</span>
          {["true","false","omit"].map(v => <button key={v} className={sel(v, fracProper)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setFracProper(v)}>{v}</button>)}
          <span style={{ color: "#aaa", marginLeft: 4 }}>Sign:</span>
          {["pos","neg","pos_neg"].map(v => <button key={v} className={sel(v, fracSign)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setFracSign(v)}>{v}</button>)}
          <button className={`btn btn-sm ${fracMixed ? "btn-primary" : "btn-outline-secondary"}`} style={{ fontSize: 11, padding: "1px 6px", marginLeft: 4 }} onClick={() => setFracMixed(m => !m)}>
            mixed
          </button>
        </>}

        {type === "decimal" && <>
          <label style={{ color: "#aaa" }}>Min:
            <input type="number" value={decMin} onChange={e => setDecMin(Number(e.target.value))}
              style={{ width: 50, marginLeft: 4, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }} />
          </label>
          <label style={{ color: "#aaa" }}>Max:
            <input type="number" value={decMax} onChange={e => setDecMax(Number(e.target.value))}
              style={{ width: 50, marginLeft: 4, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }} />
          </label>
          <label style={{ color: "#aaa" }}>Decimal places:
            <input type="number" value={decPlaces} onChange={e => setDecPlaces(Number(e.target.value))} min={0} max={4}
              style={{ width: 40, marginLeft: 4, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }} />
          </label>
        </>}

        {type === "dollar" && <>
          <span style={{ color: "#aaa" }}>Size:</span>
          {["small","medium","large"].map(v => <button key={v} className={sel(v, dollarSize)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setDollarSize(v)}>{v}</button>)}
          <span style={{ color: "#888", fontSize: 11, marginLeft: 4 }}>
            {dollarSize === "small" ? "whole dollars $3–$8" : dollarSize === "medium" ? "dollars & cents $3–$10" : "round amounts $10–$1000"}
          </span>
        </>}

        {type === "percent" && <>
          <button className={`btn btn-sm ${pctCommon ? "btn-primary" : "btn-outline-secondary"}`} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setPctCommon(c => !c)}>
            common
          </button>
          <span style={{ color: "#888", fontSize: 11 }}>
            {pctCommon ? "1%, 5%, 10%, 12.5%, 20%, 25%, 50%" : ""}
          </span>
          {!pctCommon && <>
            <label style={{ color: "#aaa", marginLeft: 4 }}>Min:
              <input type="number" value={pctMin} onChange={e => setPctMin(Number(e.target.value))}
                style={{ width: 50, marginLeft: 4, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }} />
            </label>
            <label style={{ color: "#aaa" }}>Max:
              <input type="number" value={pctMax} onChange={e => setPctMax(Number(e.target.value))}
                style={{ width: 50, marginLeft: 4, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }} />
            </label>
          </>}
        </>}

        {type === "choice" && <>
          <span style={{ color: "#aaa" }}>Values (comma-separated):</span>
          <input
            value={choiceVals}
            onChange={e => setChoiceVals(e.target.value)}
            style={{ width: 200, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }}
          />
        </>}

      </div>

      {/* Row 3: preview + insert */}
      <div className="d-flex align-items-start gap-3">
        <pre style={{ flex: 1, margin: 0, fontSize: 11, color: "#9cdcfe", background: "#252526", padding: "4px 8px", borderRadius: 3, overflowX: "auto" }}>
          {buildYaml()}
        </pre>
        <button
          className="btn btn-success btn-sm"
          style={{ fontSize: 12, whiteSpace: "nowrap" }}
          onClick={() => onInsert(buildYaml())}
        >
          ＋ Insert
        </button>
      </div>

    </div>
  );
}
