import { useEffect, useState, useRef } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

type Block =
  | { type: "h1"; text: string }
  | { type: "h2"; text: string; id: string }
  | { type: "h3"; text: string; id: string }
  | { type: "hr" }
  | { type: "ul"; items: string[] }
  | { type: "p"; text: string }
  | { type: "blank" }
  | { type: "table"; rows: string[][] };

function slugify(t: string) {
  return t.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function isSeparatorRow(line: string) {
  return /^\|[\s\-|:]+\|$/.test(line.trim());
}

function parseTableLine(line: string): string[] {
  return line
    .split("|")
    .slice(1, -1)
    .map((c) => c.trim());
}

function parseBlocks(text: string): Block[] {
  const lines = text.split("\n");
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith("# ")) {
      blocks.push({ type: "h1", text: line.slice(2).trim() });
      i++;
    } else if (line.startsWith("## ")) {
      const text = line.slice(3).trim();
      blocks.push({ type: "h2", text, id: slugify(text) });
      i++;
    } else if (line.startsWith("### ")) {
      const text = line.slice(4).trim();
      blocks.push({ type: "h3", text, id: slugify(text) });
      i++;
    } else if (line.trim() === "---") {
      blocks.push({ type: "hr" });
      i++;
    } else if (line.startsWith("- ")) {
      const items: string[] = [];
      while (i < lines.length && lines[i].startsWith("- ")) {
        items.push(lines[i].slice(2));
        i++;
      }
      blocks.push({ type: "ul", items });
    } else if (line.trim().startsWith("|")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      const rows = tableLines
        .filter((l) => !isSeparatorRow(l))
        .map(parseTableLine);
      blocks.push({ type: "table", rows });
    } else if (line.trim() === "") {
      blocks.push({ type: "blank" });
      i++;
    } else {
      blocks.push({ type: "p", text: line });
      i++;
    }
  }

  return blocks;
}

function formatInline(text: string): React.ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**"))
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`"))
      return (
        <code
          key={i}
          style={{
            background: "#f1f3f5",
            padding: "1px 5px",
            borderRadius: 3,
            fontSize: "0.88em",
            fontFamily: "monospace",
          }}
        >
          {part.slice(1, -1)}
        </code>
      );
    return part;
  });
}

function renderBlocks(blocks: Block[]) {
  return blocks.map((block, i) => {
    switch (block.type) {
      case "h1":
        return (
          <h4 key={i} className="fw-bold mb-3 mt-2" style={{ color: "#212529" }}>
            {formatInline(block.text)}
          </h4>
        );
      case "h2":
        return (
          <h5
            key={i}
            id={block.id}
            className="fw-semibold mt-5 mb-3 pb-2 border-bottom"
            style={{ color: "#212529", scrollMarginTop: 72 }}
          >
            {formatInline(block.text)}
          </h5>
        );
      case "h3":
        return (
          <h6
            key={i}
            id={block.id}
            className="fw-semibold mt-4 mb-2"
            style={{ color: "#495057", scrollMarginTop: 72 }}
          >
            {formatInline(block.text)}
          </h6>
        );
      case "hr":
        return <hr key={i} className="my-4" style={{ borderColor: "#dee2e6" }} />;
      case "ul":
        return (
          <ul key={i} style={{ paddingLeft: 20, marginBottom: 12 }}>
            {block.items.map((item, j) => (
              <li key={j} style={{ fontSize: 14, lineHeight: 1.7 }}>
                {formatInline(item)}
              </li>
            ))}
          </ul>
        );
      case "table": {
        const [header, ...body] = block.rows;
        return (
          <div key={i} className="table-responsive mb-4">
            <table className="table table-bordered table-sm" style={{ fontSize: 13 }}>
              {header && (
                <thead style={{ background: "#f8f9fa" }}>
                  <tr>
                    {header.map((cell, j) => (
                      <th key={j} style={{ fontWeight: 600, whiteSpace: "nowrap" }}>
                        {formatInline(cell)}
                      </th>
                    ))}
                  </tr>
                </thead>
              )}
              <tbody>
                {body.map((row, ri) => (
                  <tr key={ri}>
                    {row.map((cell, ci) => (
                      <td key={ci}>{formatInline(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      case "p":
        return (
          <p key={i} style={{ fontSize: 14, lineHeight: 1.7, marginBottom: 8 }}>
            {formatInline(block.text)}
          </p>
        );
      case "blank":
        return <div key={i} style={{ height: 6 }} />;
      default:
        return null;
    }
  });
}

interface TocEntry {
  id: string;
  text: string;
  level: 2 | 3;
}

function buildToc(blocks: Block[]): TocEntry[] {
  return blocks.flatMap((b): TocEntry[] => {
    if (b.type === "h2") return [{ id: b.id, text: b.text, level: 2 as const }];
    if (b.type === "h3") return [{ id: b.id, text: b.text, level: 3 as const }];
    return [];
  });
}

export function AdminMessagesDocsPage() {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [activeId, setActiveId] = useState("");
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch("/api/docs/messages/")
      .then((r) => r.json())
      .then((d) => setBlocks(parseBlocks(d.content)));
  }, []);

  const toc = buildToc(blocks);

  useEffect(() => {
    const onScroll = () => {
      const ids = toc.map((e) => e.id);
      for (const id of [...ids].reverse()) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= 100) {
          setActiveId(id);
          return;
        }
      }
      if (toc[0]) setActiveId(toc[0].id);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [toc]); // eslint-disable-line react-hooks/exhaustive-deps

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <Layout>
      <div className="d-flex" style={{ minHeight: "100vh" }}>
        {/* Sidebar TOC */}
        <nav
          style={{
            width: 240,
            flexShrink: 0,
            position: "sticky",
            top: 0,
            height: "100vh",
            overflowY: "auto",
            borderRight: "1px solid #dee2e6",
            padding: "24px 16px",
            background: "#f8f9fa",
          }}
        >
          <div
            className="fw-bold mb-3"
            style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: 1, color: "#6c757d" }}
          >
            Contents
          </div>
          {toc.map((entry) => (
            <button
              key={entry.id}
              className="btn btn-link p-0 text-start w-100"
              style={{
                fontSize: entry.level === 2 ? 13 : 12,
                paddingLeft: entry.level === 3 ? 12 : 0,
                fontWeight: activeId === entry.id ? 700 : entry.level === 2 ? 500 : 400,
                color: activeId === entry.id ? "#0d6efd" : entry.level === 2 ? "#343a40" : "#6c757d",
                textDecoration: "none",
                lineHeight: 1.8,
              } as React.CSSProperties}
              onClick={() => scrollTo(entry.id)}
            >
              {entry.text}
            </button>
          ))}
        </nav>

        {/* Content */}
        <div ref={contentRef} className="flex-grow-1 py-4 px-5" style={{ maxWidth: 860 }}>
          {renderBlocks(blocks)}
        </div>
      </div>
    </Layout>
  );
}
