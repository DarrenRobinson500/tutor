import { useParams } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { ParentNav } from "./components/ParentNav";
import "./ParentHomePage.css";

export const PRINCIPLES = [
  {
    n: "01",
    title: "Make practice a daily habit",
    text: "Twenty minutes of maths every day is far more powerful than two hours on a Sunday. Consistent repetition strengthens memory, builds fluency, and reduces anxiety before tests. Treat it like brushing teeth, non-negotiable and quick.",
    tip: "Try: same time each afternoon, before screens",
  },
  {
    n: "02",
    title: "Find and fill the gaps in foundational knowledge",
    text: "Maths is cumulative. A gap in understanding fractions makes algebra difficult. A weak grasp of multiplication slows things downstream. Before pushing forward, look back, identify the concepts that haven't clicked yet and address them directly.",
    tip: "Try: a short diagnostic quiz to pinpoint weak spots",
  },
  {
    n: "03",
    title: "Praise effort and strategy, not just correct answers",
    text: "Children who believe ability is fixed give up when things get hard. Praising the process, \"I love how you didn't give up and tried a different approach\", builds a growth mindset where struggle is seen as normal and positive, not a sign of failure.",
    tip: "Try: ask \"what did you try?\" before looking at the answer",
  },
  {
    n: "04",
    title: "Let them struggle a little",
    text: "Productive struggle is where learning happens. Resist the urge to jump in immediately when your child is stuck. Give them a minute or two to wrestle with a problem first. Confidence is built by overcoming difficulty, not avoiding it.",
    tip: "Try: \"What do you know about this problem so far?\"",
  },
  {
    n: "05",
    title: "Connect maths to the real world",
    text: "Abstract concepts stick when children see them in real life. Cooking uses fractions and ratios. Shopping involves percentages and estimation. Driving trips use time, distance, and rates. Point these out naturally, it shows maths is useful, not just a school exercise.",
    tip: "Try: involve your child in splitting a restaurant bill",
  },
  {
    n: "06",
    title: "Prioritise understanding over memorisation",
    text: "A child who understands why a method works can reconstruct it if they forget. A child who only memorised steps is lost. Ask \"can you explain that to me?\" regularly. If they can teach it back, they truly understand it.",
    tip: "Try: \"Explain it to me like I'm six years old\"",
  },
  {
    n: "07",
    title: "Watch your own attitude toward maths",
    text: "Parents who say \"I was never a maths person\" give their children permission to feel the same way. Children absorb parental attitudes. Even if you found maths hard, frame it as something that everyone can learn with regular, short practice. ",
    tip: "Try: \"Maths is tricky — let's figure it out together\"",
  },
  {
    n: "08",
    title: "Review what was learned, not just what's new",
    text: "Spaced repetition, revisiting earlier topics regularly, is the best evidence-backed way to build long-term retention. A few questions on last month's topic each week is far more effective than cramming before a test.",
    tip: "Try: one \"review question\" from a past topic each session",
  },
  {
    n: "09",
    title: "Know when to get specialist help",
    text: "Some gaps are better addressed by a specialist tutor than a parent. Often children learn differently from someone outside the family, and a good tutor can pinpoint misconceptions that are easy to overlook at home.",
    tip: "Try: a tutor who gives you feedback on specific gaps, not just homework help",
  },
  {
    n: "10",
    title: "Celebrate progress, not just grades",
    text: "A child who moves from struggling with percentages to understanding them has achieved something real, regardless of what a test score says. Recognise progress explicitly. Children who feel seen for improving are far more motivated to keep going than those chasing a mark.",
    tip: "Try: keep a visible record of topics mastered over the year",
  },
];

export function PrinciplesContent() {
  return (
    <div style={{ background: "#faf7f2" }}>

      {/* ── Hero header ──────────────────────────── */}
      <div style={{
        background: "#fdecd8",
        padding: "3.5rem 2rem 3rem",
        textAlign: "center",
        borderBottom: "3px solid #e8671a",
      }}>
        <span style={{
          display: "block",
          fontSize: "0.7rem", fontWeight: 600, letterSpacing: "0.22em",
          textTransform: "uppercase", color: "#e8671a", marginBottom: "1.1rem",
        }}>
          A guide for parents
        </span>
        <h1 style={{
          fontFamily: "Lora, Georgia, serif",
          fontSize: "clamp(1.9rem, 5vw, 3.2rem)", fontWeight: 700,
          color: "#2d2d2d", lineHeight: 1.2,
          maxWidth: 700, margin: "0 auto 1.2rem",
        }}>
          10 Principles for Helping Your Child{" "}
          <em style={{ fontStyle: "italic", color: "#e8671a" }}>Learn Maths</em>
        </h1>
        <p style={{
          color: "#7a6e65", fontSize: "1rem", fontWeight: 300,
          maxWidth: 500, margin: "0 auto", fontStyle: "italic",
        }}>
          Practical habits and mindsets that make a lasting difference
        </p>
      </div>

      {/* ── Content ──────────────────────────────── */}
      <main style={{ maxWidth: 780, margin: "0 auto", padding: "3rem 1.5rem 4rem" }}>

        <div style={{
          textAlign: "center", marginBottom: "3rem",
          paddingBottom: "2.5rem", borderBottom: "1px solid #d8cfc4",
        }}>
          <p style={{ fontSize: "1.05rem", color: "#4a4540", maxWidth: 600, margin: "0 auto", lineHeight: 1.8 }}>
            You don't need to be a maths expert to support your child. What matters are the habits, attitudes, and small daily choices that build confidence and understanding over time.
          </p>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {PRINCIPLES.map((p, i) => (
            <div key={p.n} style={{
              display: "grid",
              gridTemplateColumns: "72px 1fr",
              gap: "0 1.6rem",
              padding: "2rem 0",
              borderBottom: i < PRINCIPLES.length - 1 ? "1px solid #d8cfc4" : "none",
              alignItems: "start",
            }}>
              <div style={{
                fontFamily: "Lora, Georgia, serif",
                fontSize: "3.2rem", fontWeight: 700,
                color: "#fdecd8", lineHeight: 1,
                paddingTop: "0.15rem",
              }}>
                {p.n}
              </div>
              <div>
                <div style={{
                  fontFamily: "Lora, Georgia, serif",
                  fontSize: "1.22rem", fontWeight: 700,
                  color: "#1e1e1e", lineHeight: 1.3,
                  marginBottom: "0.55rem",
                }}>
                  {p.title}
                </div>
                <p style={{ fontSize: "0.97rem", color: "#4a4540", lineHeight: 1.78 }}>
                  {p.text}
                </p>
                <span style={{
                  display: "inline-block", marginTop: "0.7rem",
                  fontSize: "0.82rem", fontWeight: 600, letterSpacing: "0.03em",
                  color: "#e8671a", background: "#fdecd8",
                  padding: "0.28rem 0.7rem", borderRadius: 3,
                  fontStyle: "italic",
                }}>
                  {p.tip}
                </span>
              </div>
            </div>
          ))}
        </div>
      </main>

      <footer style={{
        background: "#fdecd8", color: "#7a6e65",
        textAlign: "center", fontSize: "0.8rem",
        padding: "1.8rem 1rem", letterSpacing: "0.04em",
        borderTop: "1px solid #d8cfc4",
      }}>
        <strong style={{ color: "#e8671a" }}>SubjectMatter</strong> &nbsp;·&nbsp; NSW Maths Tutoring · Built for Families
      </footer>
    </div>
  );
}

export default function ParentPrinciplesPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <div className="ph-page">
      <ParentNav parentId={id!} />
      <PrinciplesContent />
    </div>
  );
}
