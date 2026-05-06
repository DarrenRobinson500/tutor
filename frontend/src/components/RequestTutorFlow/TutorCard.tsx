import React, { useState } from 'react';
import type { Tutor, TutorSlot } from './RequestTutorFlow';

const TIME_LABEL: Record<TutorSlot['timeOfDay'], string> = {
  Morning:   'Morning before school',
  Afternoon: 'After school (3:30 to 5:00)',
  Evening:   'Evenings (5:00 to 8:00)',
};

interface TutorCardProps {
  tutor: Tutor;
  requestedSlots: TutorSlot[];
  parentHasDistributor: boolean;
  matchQuality: 'full' | 'partial';
  onSelect: (tutor: Tutor) => void;
}

function sessionCost(rate: number, hasDistributor: boolean): number {
  return rate + 6.5 + (hasDistributor ? 5.0 : 0);
}

function ordinal(n: number): string {
  if (n === 1) return '1st';
  if (n === 2) return '2nd';
  if (n === 3) return '3rd';
  return `${n}th`;
}

const DAY_FULL: Record<string, string> = {
  Mon: 'Monday', Tue: 'Tuesday', Wed: 'Wednesday',
  Thu: 'Thursday', Fri: 'Friday', Sat: 'Saturday', Sun: 'Sunday',
};

const TutorCard: React.FC<TutorCardProps> = ({
  tutor,
  requestedSlots,
  parentHasDistributor,
  matchQuality,
  onSelect,
}) => {
  const [expanded, setExpanded] = useState(false);

  const total = sessionCost(tutor.hourlyRate, parentHasDistributor);
  const isPerfect = matchQuality === 'full';

  const slotMatches = requestedSlots.map(rs => ({
    key: `${rs.day}-${rs.timeOfDay}`,
    label: `${DAY_FULL[rs.day] ?? rs.day} · ${TIME_LABEL[rs.timeOfDay]}`,
    matched: tutor.availability.some(ts => ts.day === rs.day && ts.timeOfDay === rs.timeOfDay),
  }));

  const handleCardClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return;
    setExpanded(prev => !prev);
  };

  const handleSelect = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect(tutor);
  };

  return (
    <div
      className={`rtf-tutor-card${expanded ? ' expanded' : ''}`}
      onClick={handleCardClick}
    >
      <div className="rtf-tutor-card-body">

        {/* Left — tutor info */}
        <div>
          <p className="rtf-tutor-name">{tutor.firstName} {tutor.lastInitial}.</p>
          <p className="rtf-tutor-uni">{tutor.university} · {ordinal(tutor.yearOfStudy)} Year</p>
          <div className="rtf-tutor-specs">
            {tutor.specialisations.map(s => (
              <span key={s} className="rtf-spec-pill">{s}</span>
            ))}
          </div>
        </div>

        {/* Middle — availability match */}
        <div className="rtf-match-col">
          {slotMatches.map(({ key, label, matched }) => (
            <div key={key} className={`rtf-match-row${matched ? '' : ' unmatched'}`}>
              <span className="rtf-match-icon" style={{ color: matched ? 'var(--sm-success)' : '#f59e0b' }}>
                {matched ? '✓' : '●'}
              </span>
              <span>{label}</span>
            </div>
          ))}
          {isPerfect && slotMatches.length > 0 && (
            <span className="rtf-perfect-badge">✓ Perfect match</span>
          )}
        </div>

        {/* Right — pricing */}
        <div className="rtf-price-col">
          {tutor.rating !== undefined ? (
            <span className="rtf-rating">
              <span style={{ color: '#f59e0b' }}>★</span>{' '}
              {tutor.rating.toFixed(1)} ({tutor.sessionCount} sessions)
            </span>
          ) : (
            <span className="rtf-new-tutor">New tutor</span>
          )}

          <span className="rtf-hourly-rate">${tutor.hourlyRate} / hr</span>

          <div className="rtf-total-wrapper">
            <span className="rtf-total-label">Total: ${total.toFixed(2)} / session</span>
            <div className="rtf-tooltip">
              <div>Tutor &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ${tutor.hourlyRate.toFixed(2)}</div>
              <div>Platform &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; $6.50</div>
              {parentHasDistributor && <div>Distributor &nbsp; $5.00</div>}
            </div>
          </div>

          {!expanded && (
            <button className="sm-btn-secondary" onClick={handleSelect}>
              Select {tutor.firstName}
            </button>
          )}
        </div>
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="rtf-tutor-details">
          <div style={{ flex: 1 }}>
            <p className="rtf-tutor-bio">{tutor.bio}</p>
            {tutor.sessionCount !== undefined && (
              <p className="rtf-session-count">{tutor.sessionCount} sessions completed</p>
            )}
          </div>
          <button className="sm-btn-primary" onClick={handleSelect}>
            Select {tutor.firstName}
          </button>
        </div>
      )}
    </div>
  );
};

export default TutorCard;
