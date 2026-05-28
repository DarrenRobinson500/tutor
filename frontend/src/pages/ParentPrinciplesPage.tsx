import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiFetch } from "../utils/apiFetch";
import { dashboardPath } from "../utils/dashboardPath";
import "./ParentHomePage.css";

const PRINCIPLES = [
  {
    n: "01",
    title: "Make practice a daily habit — not an event",
    text: "Twenty minutes of maths every day is far more powerful than two hours on a Sunday. Consistent repetition strengthens memory, builds fluency, and reduces anxiety before tests. Treat it like brushing teeth — non-negotiable and quick.",
    tip: "Try: same time each afternoon, before screens",
  },
  {
    n: "02",
    title: "Find and fill the gaps in foundational knowledge",
    text: "Maths is cumulative. A shaky understanding of fractions makes algebra painful. A weak grasp of multiplication slows everything downstream. Before pushing forward, look back — identify exactly which concepts haven't clicked and address them directly.",
    tip: "Try: a short diagnostic quiz to pinpoint weak spots",
  },
  {
    n: "03",
    title: "Praise effort and strategy, not just correct answers",
    text: "Children who believe ability is fixed give up when things get hard. Praising the process — \"I love how you tried a different approach\" — builds a growth mindset where struggle is seen as normal, not a sign of failure.",
    tip: "Try: ask \"what did you try?\" before looking at the answer",
  },
  {
    n: "04",
    title: "Let them struggle — a little",
    text: "Productive struggle is where real learning happens. Resist the urge to jump in immediately when your child is stuck. Give them a minute or two to wrestle with a problem first. Confidence is built by overcoming difficulty, not avoiding it.",
    tip: "Try: \"What do you know about this problem so far?\"",
  },
  {
    n: "05",
    title: "Connect maths to the real world",
    text: "Abstract concepts stick when children see them in real life. Cooking uses fractions and ratios. Shopping involves percentages and estimation. Driving trips use time, distance, and rates. Point these out naturally — it shows maths is useful, not just a school exercise.",
    tip: "Try: involve your child in splitting a restaurant bill",
  },
  {
    n: "06",
    title: "Prioritise understanding over memorisation",
    text: "A child who understands why a method works can reconstruct it if they forget. A child who only memorised steps is lost. Ask \"can you explain that to me?\" regularly — if they can teach it back, they truly understand it.",
    tip: "Try: \"Explain it to me like I'm six years old\"",
  },
  {
    n: "07",
    title: "Watch your own attitude toward maths",
    text: "Parents who say \"I was never a maths person\" give their children permission to feel the same way. Children absorb parental attitudes. Even if you found maths hard, frame it as something that takes practice — not a talent some people are simply born without.",
    tip: "Try: \"Maths is tricky — let's figure it out together\"",
  },
  {
    n: "08",
    title: "Review what was learned, not just what's new",
    text: "Spaced repetition — revisiting earlier topics regularly — is one of the most evidence-backed ways to build long-term retention. A few questions on last month's topic each week is far more effective than cramming before a test.",
    tip: "Try: one \"review question\" from a past topic each session",
  },
  {
    n: "09",
    title: "Know when to get specialist help",
    text: "Some gaps are better addressed by a specialist tutor than a parent. There's no shame in this — often children learn differently from someone outside the family, and a good tutor can pinpoint misconceptions that are easy to overlook at home.",
    tip: "Try: a tutor who gives you feedback on specific gaps, not just homework help",
  },
  {
    n: "10",
    title: "Celebrate progress, not just grades",
    text: "A child who moves from struggling with percentages to understanding them has achieved something real — regardless of what a test score says. Recognise progress explicitly. Children who feel seen for improving are far more motivated to keep going than those chasing a mark.",
    tip: "Try: keep a visible record of topics mastered over the year",
  },
];

export default function ParentPrinciplesPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const storedUser = (() => { try { return JSON.parse(localStorage.getItem("user") ?? "{}"); } catch { return {}; } })();
  const parentName = [storedUser.first_name, storedUser.last_name].filter(Boolean).join(" ");

  const [hasTutor, setHasTutor] = useState(false);

  useEffect(() => {
    apiFetch("/api/auth/parent_home/")
      .then(r => r.json())
      .then((data: { children?: { tutor_name?: string | null }[] }) => {
        setHasTutor((data.children ?? []).some((c) => c.tutor_name));
      })
      .catch(() => {});
  }, []);

  function handleLogout() {
    localStorage.removeItem("access");
    localStorage.removeItem("refresh");
    localStorage.removeItem("user");
    navigate("/login?tab=parent");
  }

  return (
    <div className="ph-page" style={{ background: "#faf7f2" }}>

      {/* ── Navbar ───────────────────────────────── */}
      <nav className="ph-nav">
        <div className="ph-nav-left">
          <Link to={dashboardPath()} className="ph-nav-logo">
            <img src="/subjectmatter_wordmark.svg" alt="SubjectMatter" />
          </Link>
          <div className="ph-nav-links">
            <Link to={`/parents/${id}`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Dashboard</Link>
            {hasTutor && <Link to={`/parents/${id}/bookings`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Bookings</Link>}
            {hasTutor && <Link to={`/parents/${id}/payments`} className="ph-nav-logout" style={{ textDecoration: "none" }}>Payments</Link>}
          </div>
        </div>
        <div className="ph-nav-right">
          {parentName && <span className="ph-nav-user">{parentName}</span>}
          <button className="ph-nav-logout" onClick={handleLogout}>Sign out</button>
        </div>
      </nav>

      {/* ── Hero header ──────────────────────────── */}
      <div style={{
        background: "#1e1e1e",
        padding: "3.5rem 2rem 3rem",
        textAlign: "center",
        position: "relative",
        overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", inset: 0,
          background: "repeating-linear-gradient(-45deg, transparent, transparent 24px, rgba(232,103,26,0.06) 24px, rgba(232,103,26,0.06) 25px)",
        }} />
        <div style={{ position: "relative", zIndex: 1 }}>
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
            color: "#fff", lineHeight: 1.2,
            maxWidth: 700, margin: "0 auto 1.2rem",
          }}>
            10 Principles for Helping Your Child{" "}
            <em style={{ fontStyle: "italic", color: "#f5924a" }}>Learn Maths</em>
          </h1>
          <p style={{
            color: "#b8b0a8", fontSize: "1rem", fontWeight: 300,
            maxWidth: 500, margin: "0 auto", fontStyle: "italic",
          }}>
            Practical habits and mindsets that make a lasting difference
          </p>
        </div>
      </div>
      <div style={{ height: 5, background: "linear-gradient(90deg, #e8671a, #f5924a)" }} />

      {/* ── Content ──────────────────────────────── */}
      <main style={{ maxWidth: 780, margin: "0 auto", padding: "3rem 1.5rem 4rem" }}>

        <div style={{
          textAlign: "center", marginBottom: "3rem",
          paddingBottom: "2.5rem", borderBottom: "1px solid #d8cfc4",
        }}>
          <p style={{ fontSize: "1.05rem", color: "#4a4540", maxWidth: 600, margin: "0 auto", lineHeight: 1.8 }}>
            You don't need to be a maths expert to support your child. What matters most are the habits, attitudes, and small daily choices that build confidence and genuine understanding over time.
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
        background: "#1e1e1e", color: "#888",
        textAlign: "center", fontSize: "0.8rem",
        padding: "1.8rem 1rem", letterSpacing: "0.04em",
      }}>
        <strong style={{ color: "#e8671a" }}>SubjectMatter</strong> &nbsp;·&nbsp; NSW Maths Tutoring · Built for Families
      </footer>
    </div>
  );
}
