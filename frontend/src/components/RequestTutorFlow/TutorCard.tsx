import React from 'react';
import type { Tutor, TutorSlot } from './RequestTutorFlow';

const TIME_LABEL: Record<TutorSlot['timeOfDay'], string> = {
  Morning:   'Morning before school',
  Afternoon: 'After school (3:30 to 5:00)',
  Evening:   'Evenings (5:00 to 8:00)',
};

const DAY_FULL: Record<string, string> = {
  Mon: 'Monday', Tue: 'Tuesday', Wed: 'Wednesday',
  Thu: 'Thursday', Fri: 'Friday', Sat: 'Saturday', Sun: 'Sunday',
};

interface TutorCardProps {
  tutor: Tutor;
  requestedSlots: TutorSlot[];
  parentHasDistributor: boolean;
  matchQuality: 'full' | 'partial';
  platformFee?: number;
  onSelect: (tutor: Tutor) => void;
}

function sessionCost(rate: number, hasDistributor: boolean, platformFee: number): number {
  return rate + platformFee + (hasDistributor ? 5.0 : 0);
}

function ordinal(n: number): string {
  if (n === 1) return '1st';
  if (n === 2) return '2nd';
  if (n === 3) return '3rd';
  return `${n}th`;
}

const TutorCard: React.FC<TutorCardProps> = ({
  tutor,
  requestedSlots,
  parentHasDistributor,
  matchQuality,
  platformFee = 6.5,
  onSelect,
}) => {
  const total = sessionCost(tutor.hourlyRate, parentHasDistributor, platformFee);
  const isPerfect = matchQuality === 'full';

  const matchedSlots = requestedSlots.filter(rs =>
    tutor.availability.some(ts => ts.day === rs.day && ts.timeOfDay === rs.timeOfDay)
  );

  return (
    <div className="rtf-tutor-card">
      <div className="rtf-tutor-card-body">

        {/* Left — tutor info */}
        <div>
          <p className="rtf-tutor-name">{tutor.firstName} {tutor.lastInitial}.</p>
          {(tutor.university || tutor.qualification || tutor.yearOfStudy) && (
            <p className="rtf-tutor-uni">
              {[
                tutor.university,
                tutor.yearOfStudy ? `${ordinal(tutor.yearOfStudy)} Year` : null,
                tutor.qualification,
              ].filter(Boolean).join(' · ')}
            </p>
          )}
          {tutor.specialisations && tutor.specialisations.length > 0 && (
            <div className="rtf-tutor-specs">
              {tutor.specialisations.map(s => (
                <span key={s} className="rtf-spec-pill">{s}</span>
              ))}
            </div>
          )}
        </div>

        {/* Middle — availability match */}
        {matchedSlots.length > 0 && (
          <div className="rtf-match-col">
            {matchedSlots.map(rs => (
              <div key={`${rs.day}-${rs.timeOfDay}`} className="rtf-match-row">
                <span className="rtf-match-icon" style={{ color: 'var(--sm-success)' }}>✓</span>
                <span>{DAY_FULL[rs.day] ?? rs.day} · {TIME_LABEL[rs.timeOfDay]}</span>
              </div>
            ))}
            {isPerfect && (
              <span className="rtf-perfect-badge">✓ Perfect match</span>
            )}
          </div>
        )}

        {/* Right — pricing */}
        <div className="rtf-price-col">
          {tutor.rating != null ? (
            <span className="rtf-rating">
              <span style={{ color: '#f59e0b' }}>★</span>{' '}
              {tutor.rating.toFixed(1)} ({tutor.sessionCount} sessions)
            </span>
          ) : (
            <span className="rtf-new-tutor">New tutor</span>
          )}

          <span className="rtf-hourly-rate">${total.toFixed(2)} / session</span>
        </div>
      </div>

      {tutor.bio && (
        <div className="rtf-tutor-card-footer">
          <p className="rtf-tutor-bio">{tutor.bio}</p>
          <button className="sm-btn-primary" onClick={() => onSelect(tutor)}>
            Select {tutor.firstName}
          </button>
        </div>
      )}
    </div>
  );
};

export default TutorCard;
