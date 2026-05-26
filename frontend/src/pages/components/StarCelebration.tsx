import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import "./StarCelebration.css";

interface Props {
  starCount: number;
  studentId: string | number;
}

const SPARKLES = [
  { size: 13, color: "#FFCA3A" },
  { size: 9,  color: "#FF8C42" },
  { size: 11, color: "#FFCA3A" },
  { size: 8,  color: "#FFB07A" },
  { size: 13, color: "#FF8C42" },
  { size: 9,  color: "#FFCA3A" },
  { size: 11, color: "#FF8C42" },
  { size: 8,  color: "#FFCA3A" },
  { size: 12, color: "#FFB07A" },
  { size: 9,  color: "#FF8C42" },
  { size: 11, color: "#FFCA3A" },
  { size: 8,  color: "#FFB07A" },
];

export function StarCelebration({ starCount, studentId }: Props) {
  const navigate = useNavigate();
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const goHome = () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    navigate(`/students/${studentId}`);
  };

  useEffect(() => {
    timerRef.current = setTimeout(goHome, 3500);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="sc-overlay" onClick={goHome}>
      <div className="sc-inner">

        <div className="sc-burst">
          {SPARKLES.map((sp, i) => {
            const angle = i * (360 / SPARKLES.length);
            const dist  = 70 + (i % 3) * 18;
            const delay = 0.12 + i * 0.025;
            return (
              <div
                key={i}
                className="sc-sparkle"
                style={{
                  width:  sp.size,
                  height: sp.size,
                  background: sp.color,
                  "--sc-angle": `${angle}deg`,
                  "--sc-dist":  `${dist}px`,
                  "--sc-delay": `${delay}s`,
                } as React.CSSProperties}
              />
            );
          })}
          <div className="sc-star">★</div>
        </div>

        <h1 className="sc-heading">You earned a star!</h1>
        <p className="sc-count">
          You now have <strong>{starCount}</strong> star{starCount !== 1 ? "s" : ""}
        </p>
        <p className="sc-hint">Tap anywhere to continue</p>

      </div>
    </div>
  );
}
