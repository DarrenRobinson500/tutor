import { useState } from "react";

type DiagramType =
  | "Triangle" | "Rect" | "Circle" | "Line"
  | "Prism" | "Net" | "CompositeSolid" | "AlgebraTable" | "DataTable"
  | "Cartesian" | "NumberLine" | "Angle" | "ParallelLines"
  | "DotArray" | "Clock" | "Polygon" | "Balls"
  | "GraphLine" | "GraphColumn" | "GraphPie" | "DiceSumGrid"
  | "FractionBar";

const SHAPES: { id: DiagramType; label: string }[] = [
  { id: "Triangle",     label: "Triangle"      },
  { id: "Rect",         label: "Rect"          },
  { id: "Circle",       label: "Circle"        },
  { id: "Line",         label: "Line"          },
  { id: "Prism",        label: "Prism"         },
  { id: "Net",          label: "Net"           },
  { id: "AlgebraTable", label: "AlgebraTable"  },
  { id: "DataTable",    label: "DataTable"     },
  { id: "Cartesian",    label: "Cartesian"     },
  { id: "NumberLine",   label: "NumberLine"    },
  { id: "Angle",        label: "Angle"         },
  { id: "ParallelLines",label: "ParallelLines" },
  { id: "DotArray",     label: "DotArray"      },
  { id: "Clock",        label: "Clock"         },
  { id: "Polygon",      label: "Polygon"       },
  { id: "Balls",        label: "Balls"         },
  { id: "GraphLine",    label: "GraphLine"     },
  { id: "GraphColumn",  label: "GraphColumn"   },
  { id: "GraphPie",     label: "GraphPie"      },
  { id: "DiceSumGrid",  label: "DiceSumGrid"   },
  { id: "FractionBar",  label: "FractionBar"   },
];

const NET_SHAPES = ["rect_prism","cylinder","cone","rect_pyramid","tri_prism","tri_pyramid"] as const;
type NetShape = typeof NET_SHAPES[number];

const NET_PARTS: Record<NetShape, string[]> = {
  rect_prism:   ["top", "front", "bottom", "left", "right", "back"],
  cylinder:     ["rect", "top", "bottom"],
  cone:         ["sector", "base"],
  rect_pyramid: ["base", "front", "back", "left", "right"],
  tri_prism:    ["rect_a", "rect_b", "rect_c", "tri_top", "tri_bottom"],
  tri_pyramid:  ["base", "face_a", "face_b", "face_c"],
};

interface Props {
  onInsert: (yaml: string) => void;
}

export function DiagramHelper({ onInsert }: Props) {
  const [shape, setShape] = useState<DiagramType>("Triangle");

  // Triangle — any subset of sides a,b,c and angles A,B,C (degrees)
  const [triSideA,       setTriSideA]       = useState("{{ a }}");
  const [triSideB,       setTriSideB]       = useState("{{ b }}");
  const [triSideC,       setTriSideC]       = useState("");
  const [triAngA,        setTriAngA]        = useState("");
  const [triAngB,        setTriAngB]        = useState("");
  const [triAngC,        setTriAngC]        = useState("{{ C }}");
  const [triLabelV,      setTriLabelV]      = useState(true);
  const [triAngleLabels, setTriAngleLabels] = useState(false);
  const [triLblA,        setTriLblA]        = useState("");
  const [triLblB,        setTriLblB]        = useState("");
  const [triLblC,        setTriLblC]        = useState("");
  const [triLblAngA,     setTriLblAngA]     = useState("");
  const [triLblAngB,     setTriLblAngB]     = useState("");
  const [triLblAngC,     setTriLblAngC]     = useState("");

  // Rect
  const [rectW,      setRectW]      = useState("{{ w }}");
  const [rectH,      setRectH]      = useState("{{ h }}");
  const [rectLabels, setRectLabels] = useState(true);

  // Circle
  const [circR,      setCircR]      = useState("{{ r }}");
  const [circLabels, setCircLabels] = useState(true);

  // Line
  const [lineX1,    setLineX1]    = useState("-10");
  const [lineY1,    setLineY1]    = useState("0");
  const [lineX2,    setLineX2]    = useState("10");
  const [lineY2,    setLineY2]    = useState("0");
  const [lineLS,    setLineLS]    = useState("");
  const [lineLE,    setLineLE]    = useState("");
  const [lineLM,    setLineLM]    = useState("");

  // Prism
  const [prismType,   setPrismType]   = useState<"tri"|"rect">("tri");
  const [prismA,      setPrismA]      = useState("{{ a }}");
  const [prismB,      setPrismB]      = useState("{{ b }}");
  const [prismC,      setPrismC]      = useState("{{ c }}");
  const [prismW,      setPrismW]      = useState("{{ w }}");
  const [prismHh,     setPrismHh]     = useState("{{ h }}");
  const [prismDepth,  setPrismDepth]  = useState("{{ d }}");
  const [prismLabels, setPrismLabels] = useState(true);
  const [prismLabelH, setPrismLabelH] = useState("");

  // Net
  const [netShape,   setNetShape]   = useState<NetShape>("rect_prism");
  const [netHidden,  setNetHidden]  = useState<Set<string>>(new Set());
  const [netWidth,   setNetWidth]   = useState("{{ w }}");
  const [netHeight,  setNetHeight]  = useState("{{ h }}");
  const [netDepth,   setNetDepth]   = useState("{{ d }}");
  const [netRadius,  setNetRadius]  = useState("{{ r }}");
  const [netSlant,   setNetSlant]   = useState("{{ l }}");
  const [netA,       setNetA]       = useState("{{ a }}");
  const [netB,       setNetB]       = useState("{{ b }}");
  const [netC,       setNetC]       = useState("{{ c }}");

  // AlgebraTable
  const [atXMin,  setAtXMin]  = useState("1");
  const [atXMax,  setAtXMax]  = useState("7");
  const [atExpr,  setAtExpr]  = useState("x+2");
  const [atBlank, setAtBlank] = useState("{{ blank }}");

  // DataTable
  const [dtHeaders,  setDtHeaders]  = useState("Month, Rainfall");
  const [dtRows,     setDtRows]     = useState("Jan, {{ r1 }}\nFeb, {{ r2 }}\nMar, {{ r3 }}");
  const [dtLabelCol, setDtLabelCol] = useState(false);

  // Cartesian
  const [cartXMin, setCartXMin] = useState("-6");
  const [cartXMax, setCartXMax] = useState("6");
  const [cartYMin, setCartYMin] = useState("-9");
  const [cartYMax, setCartYMax] = useState("9");
  const [cartEq,   setCartEq]   = useState("{{ m }}*x + {{ b }}");

  // NumberLine
  const [nlMin,    setNlMin]    = useState("0");
  const [nlMax,    setNlMax]    = useState("20");
  const [nlPos,    setNlPos]    = useState("");
  const [nlArrows, setNlArrows] = useState("");

  // Angle
  const [angleVal, setAngleVal] = useState("{{ angle }}");

  // ParallelLines
  const [plAngle, setPlAngle] = useState("{{ angle }}");

  // DotArray
  const [dotCount, setDotCount] = useState("3x4");

  // Clock
  const [clockTime, setClockTime] = useState("10:00");

  // Polygon
  const [polyS,      setPolyS]      = useState("5, 5, 5, 5");
  const [polyLabels, setPolyLabels] = useState(true);
  const [polyName,   setPolyName]   = useState("");

  // Balls
  const [ballRed,    setBallRed]    = useState("3");
  const [ballBlue,   setBallBlue]   = useState("2");
  const [ballGreen,  setBallGreen]  = useState("0");
  const [ballYellow, setBallYellow] = useState("0");
  const [ballWhite,  setBallWhite]  = useState("0");

  // GraphLine / GraphColumn / GraphPie — shared points string
  const [graphPoints,  setGraphPoints]  = useState(`("Jan", 5), ("Feb", 8), ("Mar", 6)`);
  const [graphYLabel,  setGraphYLabel]  = useState("");

  // DiceSumGrid
  const [diceTarget, setDiceTarget] = useState("{{ target }}");

  // FractionBar
  const [fbA,        setFbA]        = useState("{{ a }}");
  const [fbMode,     setFbMode]     = useState<"b"|"den">("den");
  const [fbB,        setFbB]        = useState("{{ b }}");
  const [fbDen,      setFbDen]      = useState("{{ den }}");
  const [fbLabel,    setFbLabel]    = useState(true);
  const [fbLabelDen, setFbLabelDen] = useState(false);

  // ── build diagram string ─────────────────────────────────────────────────

  function buildDiagram(): string {
    switch (shape) {
      case "Triangle": {
        const parts: string[] = [];
        if (triSideA.trim()) parts.push(`a: ${triSideA.trim()}`);
        if (triSideB.trim()) parts.push(`b: ${triSideB.trim()}`);
        if (triSideC.trim()) parts.push(`c: ${triSideC.trim()}`);
        if (triAngA.trim())  parts.push(`A: ${triAngA.trim()}`);
        if (triAngB.trim())  parts.push(`B: ${triAngB.trim()}`);
        if (triAngC.trim())  parts.push(`C: ${triAngC.trim()}`);
        if (triLabelV)               parts.push("label_v: true");
        if (triAngleLabels)          parts.push("angle_labels: true");
        if (triLblA.trim())          parts.push(`label_a: "${triLblA.trim()}"`);
        if (triLblB.trim())          parts.push(`label_b: "${triLblB.trim()}"`);
        if (triLblC.trim())          parts.push(`label_c: "${triLblC.trim()}"`);
        if (triLblAngA.trim())       parts.push(`label_A: "${triLblAngA.trim()}"`);
        if (triLblAngB.trim())       parts.push(`label_B: "${triLblAngB.trim()}"`);
        if (triLblAngC.trim())       parts.push(`label_C: "${triLblAngC.trim()}"`);
        return `Triangle(${parts.join(", ")})`;
      }
      case "Rect": {
        const parts = [`width: ${rectW}`, `height: ${rectH}`];
        if (rectLabels) parts.push("labels: true");
        return `Rect(${parts.join(", ")})`;
      }
      case "Circle": {
        const parts = [`radius: ${circR}`];
        if (circLabels) parts.push("labels: true");
        return `Circle(${parts.join(", ")})`;
      }
      case "Line": {
        const parts = [`start: (${lineX1}, ${lineY1})`, `end: (${lineX2}, ${lineY2})`];
        if (lineLS) parts.push(`label_s: "${lineLS}"`);
        if (lineLE) parts.push(`label_e: "${lineLE}"`);
        if (lineLM) parts.push(`label_m: "${lineLM}"`);
        return `Line(${parts.join(", ")})`;
      }
      case "Prism": {
        const sides = prismType === "tri"
          ? `[${prismA}, ${prismB}, ${prismC}]`
          : `[${prismW}, ${prismHh}, ${prismW}, ${prismHh}]`;
        const parts = [`sides: ${sides}`, `depth: ${prismDepth}`];
        if (prismLabels) parts.push("labels: true");
        if (prismLabelH) parts.push(`label_h: "${prismLabelH}"`);
        return `Prism(${parts.join(", ")})`;
      }
      case "Net": {
        const parts: string[] = [`shape: ${netShape}`];
        if (netShape === "rect_prism") {
          parts.push(`width: ${netWidth}`, `height: ${netHeight}`, `depth: ${netDepth}`);
        } else if (netShape === "cylinder") {
          parts.push(`radius: ${netRadius}`, `height: ${netHeight}`);
        } else if (netShape === "cone") {
          parts.push(`radius: ${netRadius}`, `slant: ${netSlant}`);
        } else if (netShape === "rect_pyramid") {
          parts.push(`width: ${netWidth}`, `depth: ${netDepth}`, `height: ${netHeight}`);
        } else if (netShape === "tri_prism") {
          parts.push(`a: ${netA}`, `b: ${netB}`, `c: ${netC}`, `depth: ${netDepth}`);
        } else if (netShape === "tri_pyramid") {
          parts.push(`a: ${netA}`);
        }
        const allParts = NET_PARTS[netShape];
        const shown = allParts.filter(p => !netHidden.has(p));
        if (shown.length < allParts.length) {
          parts.push(`show: ${shown.join(",")}`);
        }
        return `Net(${parts.join(", ")})`;
      }
      case "AlgebraTable": {
        return `AlgebraTable(x_min: ${atXMin}, x_max: ${atXMax}, expr: "${atExpr}", blank: ${atBlank})`;
      }
      case "DataTable": {
        const headers = dtHeaders.split(',').map(h => h.trim()).join(', ');
        const rows = dtRows
          .split('\n')
          .map(line => line.trim())
          .filter(line => line.length > 0)
          .map(line => `(${line.split(',').map(c => c.trim()).join(', ')})`)
          .join(', ');
        const parts = [`headers: [${headers}]`, `rows: [${rows}]`];
        if (dtLabelCol) parts.push('label_col: true');
        return `DataTable(${parts.join(', ')})`;
      }
      case "Cartesian": {
        return `Cartesian(xmin: ${cartXMin}, xmax: ${cartXMax}, ymin: ${cartYMin}, ymax: ${cartYMax}, eq: "${cartEq}")`;
      }
      case "NumberLine": {
        let s = `NumberLine(min: ${nlMin}, max: ${nlMax}`;
        if (nlPos)    s += `, pos: (${nlPos})`;
        if (nlArrows) s += `, arrows: [(${nlArrows})]`;
        s += ")";
        return s;
      }
      case "Angle": {
        return `Angle(angle: ${angleVal})`;
      }
      case "ParallelLines": {
        return `ParallelLines(angle: ${plAngle})`;
      }
      case "DotArray": {
        return `DotArray(count: ${dotCount}, pos: (0, 0))`;
      }
      case "Clock": {
        return `Clock(time: ${clockTime}, pos: (0, 0))`;
      }
      case "Polygon": {
        const parts = [`sides: [${polyS}]`];
        if (!polyLabels) parts.push("labels: false");
        if (polyName.trim()) parts.push(`name: "${polyName.trim()}"`);
        return `Polygon(${parts.join(", ")})`;
      }
      case "Balls": {
        const parts: string[] = [];
        if (parseInt(ballRed)    > 0) parts.push(`red: ${ballRed}`);
        if (parseInt(ballBlue)   > 0) parts.push(`blue: ${ballBlue}`);
        if (parseInt(ballGreen)  > 0) parts.push(`green: ${ballGreen}`);
        if (parseInt(ballYellow) > 0) parts.push(`yellow: ${ballYellow}`);
        if (parseInt(ballWhite)  > 0) parts.push(`white: ${ballWhite}`);
        return `Balls(${parts.join(", ")})`;
      }
      case "GraphLine": {
        const parts = [`points: [${graphPoints}]`];
        if (graphYLabel.trim()) parts.push(`y_label: "${graphYLabel.trim()}"`);
        return `GraphLine(${parts.join(", ")})`;
      }
      case "GraphColumn": {
        return `GraphColumn(points: [${graphPoints}], pos: (0, 0))`;
      }
      case "GraphPie": {
        return `GraphPie(points: [${graphPoints}], pos: (0, 0))`;
      }
      case "DiceSumGrid": {
        return `DiceSumGrid(target: ${diceTarget}, pos: (0, 0))`;
      }
      case "FractionBar": {
        const parts = [`a: ${fbA}`];
        if (fbMode === "den") parts.push(`den: ${fbDen}`);
        else                  parts.push(`b: ${fbB}`);
        if (!fbLabel)    parts.push("label: false");
        if (fbLabelDen)  parts.push("label_den: true");
        return `FractionBar(${parts.join(", ")})`;
      }
      default:
        return "";
    }
  }

  const diagramStr = buildDiagram();
  const yaml = `diagram: '${diagramStr}'`;

  const sel = (v: string, cur: string) =>
    `btn btn-sm ${v === cur ? "btn-primary" : "btn-outline-secondary"}`;

  const inp = (
    value: string,
    onChange: (v: string) => void,
    width = 80
  ) => (
    <input
      value={value}
      onChange={e => onChange(e.target.value)}
      style={{ width, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }}
    />
  );

  const lbl = (text: string) => (
    <span style={{ color: "#aaa", whiteSpace: "nowrap" }}>{text}</span>
  );

  return (
    <div style={{ padding: "8px 10px", background: "#1e1e1e", borderTop: "1px solid #333", color: "#ccc", fontSize: 12 }}>

      {/* Row 1: shape selector */}
      <div className="d-flex align-items-center gap-1 flex-wrap mb-2">
        {SHAPES.map(s => (
          <button
            key={s.id}
            className={sel(s.id, shape)}
            style={{ fontSize: 11, padding: "1px 7px" }}
            onClick={() => setShape(s.id)}
          >
            {s.label}
          </button>
        ))}
      </div>

      {/* Row 2: shape-specific params */}
      <div className="d-flex align-items-center gap-2 flex-wrap mb-2">

        {shape === "Triangle" && <>
          {lbl("sides —")}
          {lbl("a:")} {inp(triSideA, setTriSideA, 80)}
          {lbl("b:")} {inp(triSideB, setTriSideB, 80)}
          {lbl("c:")} {inp(triSideC, setTriSideC, 80)}
          <div style={{ width: "100%" }} />
          {lbl("angles° —")}
          {lbl("A:")} {inp(triAngA, setTriAngA, 80)}
          {lbl("B:")} {inp(triAngB, setTriAngB, 80)}
          {lbl("C:")} {inp(triAngC, setTriAngC, 80)}
          <div style={{ width: "100%" }} />
          <button
            className={`btn btn-sm ${triLabelV ? "btn-primary" : "btn-outline-secondary"}`}
            style={{ fontSize: 11, padding: "1px 6px" }}
            onClick={() => setTriLabelV(v => !v)}
          >side labels</button>
          <button
            className={`btn btn-sm ${triAngleLabels ? "btn-primary" : "btn-outline-secondary"}`}
            style={{ fontSize: 11, padding: "1px 6px" }}
            onClick={() => setTriAngleLabels(v => !v)}
          >angle labels</button>
          <div style={{ width: "100%" }} />
          {lbl("label sides —")}
          {lbl("a:")} {inp(triLblA, setTriLblA, 70)}
          {lbl("b:")} {inp(triLblB, setTriLblB, 70)}
          {lbl("c:")} {inp(triLblC, setTriLblC, 70)}
          <div style={{ width: "100%" }} />
          {lbl("label angles —")}
          {lbl("A:")} {inp(triLblAngA, setTriLblAngA, 70)}
          {lbl("B:")} {inp(triLblAngB, setTriLblAngB, 70)}
          {lbl("C:")} {inp(triLblAngC, setTriLblAngC, 70)}
        </>}

        {shape === "Rect" && <>
          {lbl("width:")} {inp(rectW, setRectW)}
          {lbl("height:")} {inp(rectH, setRectH)}
          <button
            className={`btn btn-sm ${rectLabels ? "btn-primary" : "btn-outline-secondary"}`}
            style={{ fontSize: 11, padding: "1px 6px" }}
            onClick={() => setRectLabels(v => !v)}
          >labels</button>
        </>}

        {shape === "Circle" && <>
          {lbl("radius:")} {inp(circR, setCircR)}
          <button
            className={`btn btn-sm ${circLabels ? "btn-primary" : "btn-outline-secondary"}`}
            style={{ fontSize: 11, padding: "1px 6px" }}
            onClick={() => setCircLabels(v => !v)}
          >labels</button>
        </>}

        {shape === "Line" && <>
          {lbl("start:")} {inp(lineX1, setLineX1, 50)} {inp(lineY1, setLineY1, 50)}
          {lbl("end:")}   {inp(lineX2, setLineX2, 50)} {inp(lineY2, setLineY2, 50)}
          {lbl("label_s:")} {inp(lineLS, setLineLS, 60)}
          {lbl("label_e:")} {inp(lineLE, setLineLE, 60)}
          {lbl("label_m:")} {inp(lineLM, setLineLM, 80)}
        </>}

        {shape === "Prism" && <>
          <button className={sel("tri",  prismType)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setPrismType("tri")}>Triangular</button>
          <button className={sel("rect", prismType)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setPrismType("rect")}>Rectangular</button>
          <div style={{ width: "100%" }} />
          {prismType === "tri" && <>
            {lbl("a:")} {inp(prismA, setPrismA, 70)}
            {lbl("b:")} {inp(prismB, setPrismB, 70)}
            {lbl("c:")} {inp(prismC, setPrismC, 70)}
            {lbl("depth:")} {inp(prismDepth, setPrismDepth, 70)}
          </>}
          {prismType === "rect" && <>
            {lbl("w:")} {inp(prismW, setPrismW, 70)}
            {lbl("h:")} {inp(prismHh, setPrismHh, 70)}
            {lbl("depth:")} {inp(prismDepth, setPrismDepth, 70)}
          </>}
          <div style={{ width: "100%" }} />
          <button
            className={`btn btn-sm ${prismLabels ? "btn-primary" : "btn-outline-secondary"}`}
            style={{ fontSize: 11, padding: "1px 6px" }}
            onClick={() => setPrismLabels(v => !v)}
          >labels</button>
          {lbl("label_h:")} {inp(prismLabelH, setPrismLabelH, 60)}
        </>}

        {shape === "Net" && <>
          {NET_SHAPES.map(ns => (
            <button key={ns} className={sel(ns, netShape)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => { setNetShape(ns); setNetHidden(new Set()); }}>{ns}</button>
          ))}
          <div className="d-flex align-items-center gap-2 flex-wrap mt-1 w-100">
            {netShape === "rect_prism" && <>
              {lbl("w:")} {inp(netWidth, setNetWidth, 70)}
              {lbl("h:")} {inp(netHeight, setNetHeight, 70)}
              {lbl("d:")} {inp(netDepth, setNetDepth, 70)}
            </>}
            {netShape === "cylinder" && <>
              {lbl("radius:")} {inp(netRadius, setNetRadius, 70)}
              {lbl("height:")} {inp(netHeight, setNetHeight, 70)}
            </>}
            {netShape === "cone" && <>
              {lbl("radius:")} {inp(netRadius, setNetRadius, 70)}
              {lbl("slant:")}  {inp(netSlant, setNetSlant, 70)}
            </>}
            {netShape === "rect_pyramid" && <>
              {lbl("w:")} {inp(netWidth, setNetWidth, 70)}
              {lbl("d:")} {inp(netDepth, setNetDepth, 70)}
              {lbl("h:")} {inp(netHeight, setNetHeight, 70)}
            </>}
            {netShape === "tri_prism" && <>
              {lbl("a:")} {inp(netA, setNetA, 70)}
              {lbl("b:")} {inp(netB, setNetB, 70)}
              {lbl("c:")} {inp(netC, setNetC, 70)}
              {lbl("depth:")} {inp(netDepth, setNetDepth, 70)}
            </>}
            {netShape === "tri_pyramid" && <>
              {lbl("a:")} {inp(netA, setNetA, 70)}
            </>}
          </div>
          <div className="d-flex align-items-center gap-1 flex-wrap mt-1 w-100">
            {lbl("show:")}
            {NET_PARTS[netShape].map(p => {
              const hidden = netHidden.has(p);
              return (
                <button
                  key={p}
                  style={{
                    fontSize: 11, padding: "1px 6px", borderRadius: 4, border: "1px solid #aaa",
                    background: hidden ? "#e0e0e0" : "#4a90d9",
                    color: hidden ? "#666" : "#fff",
                    textDecoration: hidden ? "line-through" : "none",
                    cursor: "pointer",
                  }}
                  onClick={() => setNetHidden(prev => {
                    const next = new Set(prev);
                    if (next.has(p)) next.delete(p); else next.add(p);
                    return next;
                  })}
                >{p}</button>
              );
            })}
          </div>
        </>}

        {shape === "AlgebraTable" && <>
          {lbl("x_min:")} {inp(atXMin, setAtXMin, 50)}
          {lbl("x_max:")} {inp(atXMax, setAtXMax, 50)}
          {lbl("expr:")}  {inp(atExpr, setAtExpr, 120)}
          {lbl("blank:")} {inp(atBlank, setAtBlank, 80)}
        </>}

        {shape === "DataTable" && <>
          <div style={{ width: "100%" }}>
            {lbl("headers (comma-separated):")}
          </div>
          <input
            value={dtHeaders}
            onChange={e => setDtHeaders(e.target.value)}
            style={{ width: 300, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }}
          />
          <div style={{ width: "100%" }} />
          <div style={{ width: "100%" }}>
            {lbl("rows (one per line, comma-separated values):")}
          </div>
          <textarea
            value={dtRows}
            onChange={e => setDtRows(e.target.value)}
            rows={4}
            style={{ width: 300, fontSize: 12, padding: "2px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3, resize: "vertical", fontFamily: "monospace" }}
          />
          <div style={{ width: "100%" }} />
          <button
            className={`btn btn-sm ${dtLabelCol ? "btn-primary" : "btn-outline-secondary"}`}
            style={{ fontSize: 11, padding: "1px 6px" }}
            onClick={() => setDtLabelCol(v => !v)}
          >label_col</button>
          {lbl("— shade first column grey")}
        </>}

        {shape === "Cartesian" && <>
          {lbl("xmin:")} {inp(cartXMin, setCartXMin, 50)}
          {lbl("xmax:")} {inp(cartXMax, setCartXMax, 50)}
          {lbl("ymin:")} {inp(cartYMin, setCartYMin, 50)}
          {lbl("ymax:")} {inp(cartYMax, setCartYMax, 50)}
          {lbl("eq:")}   {inp(cartEq, setCartEq, 160)}
        </>}

        {shape === "NumberLine" && <>
          {lbl("min:")} {inp(nlMin, setNlMin, 60)}
          {lbl("max:")} {inp(nlMax, setNlMax, 60)}
          {lbl("pos (x,y):")}    {inp(nlPos, setNlPos, 80)}
          {lbl("arrows (x1,x2):")} {inp(nlArrows, setNlArrows, 100)}
        </>}

        {shape === "Angle" && <>
          {lbl("angle:")} {inp(angleVal, setAngleVal, 100)}
        </>}

        {shape === "ParallelLines" && <>
          {lbl("angle:")} {inp(plAngle, setPlAngle, 100)}
        </>}

        {shape === "DotArray" && <>
          {lbl("count (rows×cols):")} {inp(dotCount, setDotCount, 70)}
          {lbl("e.g. 3x4 or 12")}
        </>}

        {shape === "Clock" && <>
          {lbl("time:")} {inp(clockTime, setClockTime, 70)}
          {lbl("(HH:MM)")}
        </>}

        {shape === "Polygon" && <>
          {lbl("sides:")} {inp(polyS, setPolyS, 180)}
          <button
            className={`btn btn-sm ${polyLabels ? "btn-primary" : "btn-outline-secondary"}`}
            style={{ fontSize: 11, padding: "1px 6px" }}
            onClick={() => setPolyLabels(v => !v)}
          >labels</button>
          {lbl("name:")} {inp(polyName, setPolyName, 80)}
        </>}

        {shape === "Balls" && <>
          {lbl("red:")}    {inp(ballRed,    setBallRed,    40)}
          {lbl("blue:")}   {inp(ballBlue,   setBallBlue,   40)}
          {lbl("green:")}  {inp(ballGreen,  setBallGreen,  40)}
          {lbl("yellow:")} {inp(ballYellow, setBallYellow, 40)}
          {lbl("white:")}  {inp(ballWhite,  setBallWhite,  40)}
        </>}

        {(shape === "GraphLine" || shape === "GraphColumn" || shape === "GraphPie") && <>
          <div style={{ width: "100%" }}>
            {lbl(`points — e.g. ("Jan", 5), ("Feb", 8):`)}
          </div>
          <input
            value={graphPoints}
            onChange={e => setGraphPoints(e.target.value)}
            style={{ width: 340, fontSize: 12, padding: "1px 4px", background: "#2d2d2d", color: "#fff", border: "1px solid #555", borderRadius: 3 }}
          />
          {shape === "GraphLine" && <>
            {lbl("y_label:")} {inp(graphYLabel, setGraphYLabel, 100)}
          </>}
        </>}

        {shape === "DiceSumGrid" && <>
          {lbl("target:")} {inp(diceTarget, setDiceTarget, 80)}
        </>}

        {shape === "FractionBar" && <>
          {lbl("a (top):")} {inp(fbA, setFbA, 100)}
          <button className={sel("den", fbMode)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setFbMode("den")}>auto den</button>
          <button className={sel("b",   fbMode)} style={{ fontSize: 11, padding: "1px 6px" }} onClick={() => setFbMode("b")}>explicit b</button>
          {fbMode === "den"
            ? <>{lbl("den:")} {inp(fbDen, setFbDen, 80)}</>
            : <>{lbl("b (bottom):")} {inp(fbB, setFbB, 100)}</>}
          <button
            className={`btn btn-sm ${fbLabel ? "btn-primary" : "btn-outline-secondary"}`}
            style={{ fontSize: 11, padding: "1px 6px" }}
            onClick={() => setFbLabel(v => !v)}
          >label</button>
          <button
            className={`btn btn-sm ${fbLabelDen ? "btn-primary" : "btn-outline-secondary"}`}
            style={{ fontSize: 11, padding: "1px 6px" }}
            onClick={() => setFbLabelDen(v => !v)}
          >label_den</button>
        </>}

      </div>

      {/* Row 3: preview + insert */}
      <div className="d-flex align-items-start gap-3">
        <pre style={{ flex: 1, margin: 0, fontSize: 11, color: "#9cdcfe", background: "#252526", padding: "4px 8px", borderRadius: 3, overflowX: "auto", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
          {yaml}
        </pre>
        <button
          className="btn btn-success btn-sm"
          style={{ fontSize: 12, whiteSpace: "nowrap" }}
          onClick={() => onInsert(yaml)}
        >
          ＋ Insert
        </button>
      </div>

    </div>
  );
}
