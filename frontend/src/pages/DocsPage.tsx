import { useEffect, useState, useRef } from "react";
import { Layout } from "./components/Layout";
import { apiFetch } from "../utils/apiFetch";

interface Section {
  id: string;
  title: string;
  subsections: { id: string; title: string }[];
  lines: string[];
}

function slugify(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

function parseDocs(text: string): Section[] {
  const lines = text.split("\n");
  const sections: Section[] = [];
  let current: Section | null = null;
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Major section: ━━━ line, then title, then ━━━ line
    if (line.startsWith("━") && i + 2 < lines.length && lines[i + 2].startsWith("━")) {
      const title = lines[i + 1].trim();
      if (title) {
        current = { id: slugify(title), title, subsections: [], lines: [] };
        sections.push(current);
        i += 3;
        continue;
      }
    }

    // Subsection: ── Title ──────
    if (line.startsWith("──") && current) {
      const match = line.match(/^──+\s*(.+?)\s*──+/);
      if (match) {
        const subTitle = match[1].trim();
        const subId = `${current.id}--${slugify(subTitle)}`;
        current.subsections.push({ id: subId, title: subTitle });
        current.lines.push(`__SUBSECTION__${subId}__${subTitle}`);
        i++;
        continue;
      }
    }

    if (current) {
      current.lines.push(line);
    }

    i++;
  }

  return sections;
}

function renderLines(lines: string[]) {
  return lines.map((line, i) => {
    // Subsection header marker
    if (line.startsWith("__SUBSECTION__")) {
      const parts = line.split("__").filter(Boolean);
      // parts: ["SUBSECTION", id, title]
      const id = parts[1];
      const title = parts.slice(2).join("__");
      return (
        <h6
          key={i}
          id={id}
          className="mt-4 mb-2 fw-semibold border-bottom pb-1"
          style={{ color: "#495057", scrollMarginTop: 72 }}
        >
          {title}
        </h6>
      );
    }

    // Code / indented line
    if (line.startsWith("  ") && line.trim().length > 0) {
      return (
        <div
          key={i}
          style={{
            fontFamily: "monospace",
            fontSize: 13,
            whiteSpace: "pre",
            lineHeight: 1.5,
            color: "#212529",
          }}
        >
          {line}
        </div>
      );
    }

    // Empty line
    if (line.trim() === "") {
      return <div key={i} style={{ height: 8 }} />;
    }

    // Normal text
    return (
      <div key={i} style={{ lineHeight: 1.7, fontSize: 14 }}>
        {line}
      </div>
    );
  });
}

export function DocsPage() {
  const [sections, setSections] = useState<Section[]>([]);
  const [activeId, setActiveId] = useState<string>("");
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch("/api/docs/")
      .then(r => r.json())
      .then(data => {
        setSections(parseDocs(data.content));
      });
  }, []);

  // Highlight active TOC entry on scroll
  useEffect(() => {
    const onScroll = () => {
      const allIds = sections.flatMap(s => [
        s.id,
        ...s.subsections.map(sub => sub.id),
      ]);

      for (const id of [...allIds].reverse()) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top <= 100) {
          setActiveId(id);
          return;
        }
      }
      if (sections[0]) setActiveId(sections[0].id);
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [sections]);

  function scrollTo(id: string) {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <Layout>
      <div className="d-flex" style={{ minHeight: "100vh" }}>

        {/* Sidebar TOC */}
        <nav
          style={{
            width: 260,
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
          <div className="fw-bold mb-3" style={{ fontSize: 13, textTransform: "uppercase", letterSpacing: 1, color: "#6c757d" }}>
            Contents
          </div>
          {sections.map(section => (
            <div key={section.id} className="mb-1">
              <button
                className="btn btn-link p-0 text-start w-100"
                style={{
                  fontSize: 13,
                  fontWeight: activeId === section.id ? 700 : 500,
                  color: activeId === section.id ? "#0d6efd" : "#343a40",
                  textDecoration: "none",
                  lineHeight: 1.8,
                }}
                onClick={() => scrollTo(section.id)}
              >
                {section.title}
              </button>
              {section.subsections.map(sub => (
                <button
                  key={sub.id}
                  className="btn btn-link p-0 text-start w-100"
                  style={{
                    fontSize: 12,
                    paddingLeft: 12,
                    fontWeight: activeId === sub.id ? 600 : 400,
                    color: activeId === sub.id ? "#0d6efd" : "#6c757d",
                    textDecoration: "none",
                    lineHeight: 1.8,
                  } as React.CSSProperties}
                  onClick={() => scrollTo(sub.id)}
                >
                  {sub.title}
                </button>
              ))}
            </div>
          ))}
        </nav>

        {/* Main content */}
        <div ref={contentRef} className="flex-grow-1 py-4 px-5" style={{ maxWidth: 820 }}>

          {sections.map(section => (
            <section key={section.id} className="mb-5">
              <h5
                id={section.id}
                className="mb-3 pb-2 border-bottom fw-bold"
                style={{ scrollMarginTop: 72, color: "#212529" }}
              >
                {section.title}
              </h5>
              {renderLines(section.lines)}
            </section>
          ))}
        </div>

      </div>
    </Layout>
  );
}
