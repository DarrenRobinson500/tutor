import React from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

interface LatexProps {
  children: string;
}

function renderInlineMath(content: string, key: number | string) {
  try {
    const html = katex.renderToString(content, { displayMode: false, throwOnError: true });
    return <span key={key} dangerouslySetInnerHTML={{ __html: html }} />;
  } catch (err: any) {
    return <span key={key} style={{ color: "red", fontFamily: "monospace" }}>LaTeX error: {err.message}</span>;
  }
}

function renderDisplayMath(content: string, key: number | string) {
  try {
    const html = katex.renderToString(content, { displayMode: true, throwOnError: true });
    return <div key={key} className="katex-display-left" dangerouslySetInnerHTML={{ __html: html }} />;
  } catch (err: any) {
    return <span key={key} style={{ color: "red", fontFamily: "monospace" }}>LaTeX error: {err.message}</span>;
  }
}

// Splits a plain-text string into text and bare LaTeX math segments.
// e.g. "What is \frac{3}{5} + \frac{1}{2}?" →
//   [{type:"text", content:"What is "}, {type:"math", content:"\\frac{3}{5} + \\frac{1}{2}"}, {type:"text", content:"?"}]
function splitBareLatex(text: string): Array<{ type: "text" | "math"; content: string }> {
  if (!text.includes("\\")) return [{ type: "text", content: text }];

  // Split on LaTeX commands with their {} arguments (handles up to 2 levels of nesting)
  const rawParts = text.split(/(\\[a-zA-Z]+(?:\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})*)/g);

  const result: Array<{ type: "text" | "math"; content: string }> = [];
  let i = 0;

  while (i < rawParts.length) {
    const part = rawParts[i];
    if (!part) { i++; continue; }

    if (/^\\[a-zA-Z]/.test(part)) {
      // Merge consecutive math commands connected by operators/spaces
      let math = part;
      let j = i + 1;
      while (j < rawParts.length) {
        const sep = rawParts[j] ?? "";
        const next = rawParts[j + 1] ?? "";
        if (/^[\s+\-*/=^_<>|!:,.()\[\]]*$/.test(sep) && /^\\[a-zA-Z]/.test(next)) {
          math += sep + next;
          j += 2;
        } else {
          break;
        }
      }
      result.push({ type: "math", content: math });
      i = j;
    } else {
      result.push({ type: "text", content: part });
      i++;
    }
  }

  return result;
}

// Add comma thousand-separators to integers with 4+ digits in plain text.
// Only matches bare integers (not inside decimals, fractions, or after a digit).
function formatLargeIntegers(text: string): string {
  return text.replace(/(?<![\d.])\b(\d{4,})\b(?![\d.])/g, (n) => parseInt(n, 10).toLocaleString("en-AU"));
}

// Splits a plain string on ^{...} and ^X (caret superscripts) for inline rendering.
function splitSuperscripts(text: string): Array<{ type: "text" | "sup"; content: string }> {
  const result: Array<{ type: "text" | "sup"; content: string }> = [];
  const regex = /\s*\^\s*\{([^}]*)\}|\s*\^\s*\(([^)]*)\)|\s*\^\s*(-?[a-zA-Z0-9]+)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = regex.exec(text)) !== null) {
    if (m.index > last) result.push({ type: "text", content: text.slice(last, m.index) });
    result.push({ type: "sup", content: m[1] ?? m[2] ?? m[3] });
    last = m.index + m[0].length;
  }
  if (last < text.length) result.push({ type: "text", content: text.slice(last) });
  return result;
}

// Renders a text segment (possibly containing bare LaTeX) with optional bold wrapping.
function renderTextSegment(text: string, bold: boolean, key: string | number): React.ReactElement {
  const subParts = splitBareLatex(text);
  const nodes = subParts.flatMap((sp, j) => {
    if (sp.type === "math") return [renderInlineMath(sp.content, `${key}-${j}`)];
    // Split plain text on caret superscripts before rendering
    return splitSuperscripts(sp.content).map((seg, k) =>
      seg.type === "sup"
        ? <sup key={`${key}-${j}-${k}`}>{seg.content}</sup>
        : <span key={`${key}-${j}-${k}`} style={{ whiteSpace: "pre-wrap" }}>{formatLargeIntegers(seg.content)}</span>
    );
  });
  if (bold) return <strong key={key}>{nodes}</strong>;
  return <React.Fragment key={key}>{nodes}</React.Fragment>;
}

// Private-use Unicode character used as a placeholder for \$ (escaped dollar sign).
// Replaced before splitting so \$ never acts as a math delimiter.
const DOLLAR_PLACEHOLDER = "\uE000";

function renderLatexContent(children: string): React.ReactNode[] {
  // Replace \$ with placeholder so it is never treated as a math delimiter
  const text = children.replace(/\\\$/g, DOLLAR_PLACEHOLDER);

  // Split on delimited math: $$...$$, $...$, \[...\], \(...\)
  const parts = text.split(/(\${1,2}[\s\S]*?\${1,2}|\\\[[\s\S]*?\\\]|\\\([\s\S]*?\\\))/g);

  return parts.flatMap((part, i) => {
    const trimmed = part.trim();

    // Restore \$ inside math blocks so KaTeX can render a literal dollar sign
    const mathContent = (s: string) => s.replace(new RegExp(DOLLAR_PLACEHOLDER, "g"), "\\$");
    // Restore \$ in text segments as a plain $ character
    const textContent = (s: string) => s.replace(new RegExp(DOLLAR_PLACEHOLDER, "g"), "$");

    // Block math: $$ ... $$ or \[ ... \]
    if (trimmed.startsWith("$$") && trimmed.endsWith("$$")) {
      return [renderDisplayMath(mathContent(trimmed.slice(2, -2)), i)];
    }
    if (trimmed.startsWith("\\[") && trimmed.endsWith("\\]")) {
      return [renderDisplayMath(mathContent(trimmed.slice(2, -2)), i)];
    }

    // Inline math: $ ... $ or \( ... \)
    if (trimmed.startsWith("$") && trimmed.endsWith("$")) {
      return [renderInlineMath(mathContent(trimmed.slice(1, -1)), i)];
    }
    if (trimmed.startsWith("\\(") && trimmed.endsWith("\\)")) {
      return [renderInlineMath(mathContent(trimmed.slice(2, -2)), i)];
    }

    // Plain text — split on **bold** first, then render each segment through LaTeX pipeline
    const tc = textContent(part);
    const boldParts = tc.split(/(\*\*(?:[^*]|\*(?!\*))*\*\*)/g);
    return boldParts.flatMap((bp, j) => {
      const isBold = bp.startsWith("**") && bp.endsWith("**");
      const inner = isBold ? bp.slice(2, -2) : bp;
      return [renderTextSegment(inner, isBold, `${i}-${j}`)];
    });
  });
}

function isTableRow(line: string): boolean {
  return /^\s*\|.*\|\s*$/.test(line);
}

function parseTableRow(line: string): string[] {
  return line.trim().slice(1, -1).split("|").map(c => c.trim());
}

function isSeparatorRow(cells: string[]): boolean {
  return cells.length > 0 && cells.every(c => /^:?-+:?$/.test(c));
}

export function Latex({ children }: LatexProps) {
  // Split into segments: consecutive "* item" lines become bullet lists,
  // consecutive "| ... |" lines become tables;
  // everything else is rendered through the normal LaTeX pipeline.
  const lines = children.split("\n");

  type Segment =
    | { type: "bullets"; items: string[] }
    | { type: "ordered"; items: string[] }
    | { type: "table"; lines: string[] }
    | { type: "text"; lines: string[] };
  const segments: Segment[] = [];

  for (const line of lines) {
    if (/^\*\s+/.test(line)) {
      const last = segments[segments.length - 1];
      if (last?.type === "bullets") {
        last.items.push(line.replace(/^\*\s+/, ""));
      } else {
        segments.push({ type: "bullets", items: [line.replace(/^\*\s+/, "")] });
      }
    } else if (/^\d+\.\s+/.test(line)) {
      const last = segments[segments.length - 1];
      if (last?.type === "ordered") {
        last.items.push(line.replace(/^\d+\.\s+/, ""));
      } else {
        segments.push({ type: "ordered", items: [line.replace(/^\d+\.\s+/, "")] });
      }
    } else if (isTableRow(line)) {
      const last = segments[segments.length - 1];
      if (last?.type === "table") {
        last.lines.push(line);
      } else {
        segments.push({ type: "table", lines: [line] });
      }
    } else {
      const last = segments[segments.length - 1];
      if (last?.type === "text") {
        last.lines.push(line);
      } else {
        segments.push({ type: "text", lines: [line] });
      }
    }
  }

  return (
    <>
      {segments.map((seg, i) => {
        if (seg.type === "bullets") {
          return (
            <ul key={i} style={{ marginTop: 4, marginBottom: 4, paddingLeft: 24 }}>
              {seg.items.map((item, j) => (
                <li key={j}><Latex>{item}</Latex></li>
              ))}
            </ul>
          );
        }

        if (seg.type === "ordered") {
          return (
            <ol key={i} style={{ marginTop: 4, marginBottom: 4, paddingLeft: 24 }}>
              {seg.items.map((item, j) => (
                <li key={j}><Latex>{item}</Latex></li>
              ))}
            </ol>
          );
        }

        if (seg.type === "table") {
          const rows = seg.lines.map(parseTableRow);
          const sepIdx = rows.findIndex(isSeparatorRow);
          const headerRows = sepIdx > 0 ? rows.slice(0, sepIdx) : [];
          const bodyRows = sepIdx >= 0 ? rows.slice(sepIdx + 1) : rows;
          const cellStyle: React.CSSProperties = {
            border: "1px solid #d0d0d0",
            padding: "5px 10px",
            textAlign: "left",
          };
          const headStyle: React.CSSProperties = {
            ...cellStyle,
            background: "#f0f0f0",
            fontWeight: 600,
          };
          return (
            <table key={i} style={{ borderCollapse: "collapse", fontSize: "inherit", marginBottom: 8, marginTop: 4 }}>
              {headerRows.length > 0 && (
                <thead>
                  {headerRows.map((row, ri) => (
                    <tr key={ri}>
                      {row.map((cell, ci) => (
                        <th key={ci} style={headStyle}><Latex>{cell}</Latex></th>
                      ))}
                    </tr>
                  ))}
                </thead>
              )}
              <tbody>
                {bodyRows.map((row, ri) => (
                  <tr key={ri} style={ri % 2 === 1 ? { background: "#fafafa" } : {}}>
                    {row.map((cell, ci) => (
                      <td key={ci} style={cellStyle}><Latex>{cell}</Latex></td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          );
        }

        return (
          <React.Fragment key={i}>
            {renderLatexContent(seg.lines.join("\n"))}
          </React.Fragment>
        );
      })}
    </>
  );
}