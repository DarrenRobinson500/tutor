import React, { useState, useCallback, useEffect } from 'react';
import { apiFetch } from '../../utils/apiFetch';
import StepIndicator from './StepIndicator';
import TutorCard from './TutorCard';
import './RequestTutorFlow.css';

// ── Types ─────────────────────────────────────────────────────

export interface TutorSlot {
  day: 'Mon' | 'Tue' | 'Wed' | 'Thu' | 'Fri' | 'Sat' | 'Sun';
  timeOfDay: 'Morning' | 'Afternoon' | 'Evening';
  startTime?: string;  // "HH:MM"
  endTime?: string;    // "HH:MM"
}

export interface BookableSlot {
  weekday: number;
  day: string;
  dayFull: string;
  startTime: string;  // "HH:MM"
  endTime: string;    // "HH:MM"
}

export interface Tutor {
  id: string;
  firstName: string;
  lastInitial: string;
  university: string;
  qualification?: string;
  yearOfStudy?: number;
  specialisations?: string[];
  availability: TutorSlot[];
  hourlyRate: number;
  rating?: number;
  sessionCount?: number;
  bio: string;
}

export interface TutorSelection {
  tutor: Tutor;
  childName: string;
  yearGroup: number;
  focusAreas: string[];
  requestedDays: string[];
  requestedTimesOfDay: string[];
  frequency: 'once' | 'twice' | 'flexible';
  slot?: BookableSlot;
}

interface RequestTutorFlowProps {
  childName?: string;
  yearGroup?: number;
  diagnosticFocusAreas?: string[];
  parentHasDistributor: boolean;
  tutors?: Tutor[];
  confirming?: boolean;
  requestingMobile?: boolean;
  onConfirm: (selection: TutorSelection) => void;
  onRequestMobile?: (tutorId: string) => void;
  onCancel?: () => void;
}

// ── Mock tutors ───────────────────────────────────────────────

const MOCK_TUTORS: Tutor[] = [
  {
    id: '1',
    firstName: 'James',
    lastInitial: 'T',
    university: 'UNSW',
    yearOfStudy: 3,
    specialisations: ['Number & Algebra', 'Measurement & Geometry'],
    availability: [
      { day: 'Tue', timeOfDay: 'Afternoon' },
      { day: 'Thu', timeOfDay: 'Afternoon' },
      { day: 'Mon', timeOfDay: 'Morning' },
    ],
    hourlyRate: 55,
    rating: 4.8,
    sessionCount: 12,
    bio: "I'm a third-year maths student at UNSW with a passion for making abstract concepts concrete. I specialise in algebra and geometry and have helped students from Year 7 through to Year 12 HSC prep. My sessions focus on building real understanding, not just drilling formulas.",
  },
  {
    id: '2',
    firstName: 'Sarah',
    lastInitial: 'M',
    university: 'USyd',
    yearOfStudy: 2,
    specialisations: ['Statistics & Probability', 'Number & Algebra'],
    availability: [
      { day: 'Tue', timeOfDay: 'Afternoon' },
      { day: 'Thu', timeOfDay: 'Afternoon' },
      { day: 'Fri', timeOfDay: 'Evening' },
    ],
    hourlyRate: 45,
    rating: 4.6,
    sessionCount: 8,
    bio: "Second-year statistics student at USyd. I love helping students build confidence with numbers — especially those who find maths intimidating. Patient, structured, and I always revisit concepts until they click.",
  },
  {
    id: '3',
    firstName: 'Priya',
    lastInitial: 'K',
    university: 'UTS',
    yearOfStudy: 4,
    specialisations: ['Number & Algebra', 'Statistics & Probability', 'Measurement & Geometry'],
    availability: [
      { day: 'Tue', timeOfDay: 'Afternoon' },
      { day: 'Thu', timeOfDay: 'Afternoon' },
      { day: 'Sat', timeOfDay: 'Morning' },
    ],
    hourlyRate: 65,
    rating: 5.0,
    sessionCount: 3,
    bio: "Final-year maths education student at UTS. I bring a teacher's perspective to every session — focusing on the 'why' behind each method, not just the steps. Particularly strong in NSW curriculum alignment and HSC exam preparation.",
  },
  {
    id: '4',
    firstName: 'Tom',
    lastInitial: 'B',
    university: 'Macquarie',
    yearOfStudy: 1,
    specialisations: ['General catch-up / multiple areas'],
    availability: [
      { day: 'Tue', timeOfDay: 'Afternoon' },
      { day: 'Mon', timeOfDay: 'Morning' },
      { day: 'Wed', timeOfDay: 'Morning' },
    ],
    hourlyRate: 35,
    bio: "First-year maths student at Macquarie, fresh from the HSC. I know exactly what it feels like to tackle challenging problems for the first time and I'm great at breaking things down in plain language. Happy to cover any area across Years 7–10.",
  },
  {
    id: '5',
    firstName: 'Amy',
    lastInitial: 'C',
    university: 'USyd',
    yearOfStudy: 3,
    specialisations: ['Statistics & Probability', 'Measurement & Geometry'],
    availability: [
      { day: 'Thu', timeOfDay: 'Afternoon' },
      { day: 'Wed', timeOfDay: 'Morning' },
      { day: 'Fri', timeOfDay: 'Afternoon' },
    ],
    hourlyRate: 50,
    rating: 4.2,
    sessionCount: 15,
    bio: "Third-year science student with a focus on statistics and data. I'm experienced with primary and early secondary students and I make probability and data analysis engaging rather than daunting.",
  },
  {
    id: '6',
    firstName: 'Marcus',
    lastInitial: 'L',
    university: 'UNSW',
    yearOfStudy: 4,
    specialisations: ['Number & Algebra', 'Measurement & Geometry'],
    availability: [
      { day: 'Mon', timeOfDay: 'Afternoon' },
      { day: 'Tue', timeOfDay: 'Afternoon' },
      { day: 'Thu', timeOfDay: 'Morning' },
    ],
    hourlyRate: 75,
    rating: 4.9,
    sessionCount: 25,
    bio: "Final-year advanced mathematics student at UNSW with 25 sessions completed. I specialise in extension content and complex problem-solving for senior students aiming for Band 6.",
  },
];

// ── Constants ─────────────────────────────────────────────────

const FOCUS_OPTIONS = [
  'Number & Algebra',
  'Measurement & Geometry',
  'Statistics & Probability',
  'General catch-up / multiple areas',
];

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;

const TIME_OPTIONS = [
  { value: 'Morning' as const,   icon: '🌅', label: 'Morning before school' },
  { value: 'Afternoon' as const, icon: '☀️', label: 'After school (3:30pm to 5:00pm)' },
  { value: 'Evening' as const,   icon: '🌙', label: 'Evenings (5:00pm to 8:00pm)' },
];

const TIME_LABEL: Record<TutorSlot['timeOfDay'], string> = {
  Morning:   'Morning before school',
  Afternoon: 'After school (3:30pm to 5:00pm)',
  Evening:   'Evenings (5:00pm to 8:00pm)',
};

const FREQ_OPTIONS = [
  { value: 'once' as const,     label: 'Once a week' },
  { value: 'twice' as const,    label: 'Twice a week' },
  { value: 'flexible' as const, label: 'Flexible / as needed' },
];

const STEP_LABELS = ['Availability', 'Choose Tutor'];

// ── Helpers ───────────────────────────────────────────────────

const DAY_FULL: Record<string, string> = {
  Mon: 'Mondays', Tue: 'Tuesdays', Wed: 'Wednesdays',
  Thu: 'Thursdays', Fri: 'Fridays', Sat: 'Saturdays', Sun: 'Sundays',
};

const DAY_SINGLE: Record<string, string> = {
  Mon: 'Monday', Tue: 'Tuesday', Wed: 'Wednesday',
  Thu: 'Thursday', Fri: 'Friday', Sat: 'Saturday', Sun: 'Sunday',
};

function joinList(items: string[]): string {
  if (items.length === 0) return '';
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
}

function buildSummary(days: string[], times: string[], freq: string): string {
  const parts: string[] = [];
  if (days.length > 0) {
    parts.push(`on ${joinList(days.map(d => DAY_FULL[d] ?? d))}`);
  }
  if (times.length > 0) {
    const labels = times.map(v => TIME_LABEL[v as TutorSlot['timeOfDay']] ?? v);
    parts.push(labels.length === 1 ? labels[0] : `${labels.slice(0, -1).join(', ')} or ${labels[labels.length - 1]}`);
  }
  if (freq === 'once') parts.push('once a week');
  else if (freq === 'twice') parts.push('twice a week');
  else if (freq === 'flexible') parts.push('flexibly');
  return parts.length ? `You're looking for a tutor available ${parts.join(', ')}.` : '';
}

function scheduleLine(days: string[], times: string[]): string {
  const d = joinList(days.map(d => DAY_SINGLE[d] ?? d));
  const t = times.map(v => TIME_LABEL[v as TutorSlot['timeOfDay']] ?? v).join(' / ');
  return [d, t].filter(Boolean).join(' · ');
}

function sessionCost(rate: number, hasDistributor: boolean): number {
  return rate + 6.5 + (hasDistributor ? 5.0 : 0);
}

function formatTime(hhmm: string): string {
  const [hStr, mStr] = hhmm.split(':');
  const h = parseInt(hStr, 10);
  const m = parseInt(mStr, 10);
  const period = h < 12 ? 'am' : 'pm';
  const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h;
  return m === 0 ? `${h12}${period}` : `${h12}:${mStr}${period}`;
}

function buildSlots(days: string[], times: string[]): TutorSlot[] {
  const slots: TutorSlot[] = [];
  for (const day of days as TutorSlot['day'][]) {
    for (const time of times as TutorSlot['timeOfDay'][]) {
      slots.push({ day, timeOfDay: time });
    }
  }
  return slots;
}

type MatchQuality = 'full' | 'partial' | 'none';

function matchQuality(tutor: Tutor, slots: TutorSlot[]): MatchQuality {
  if (slots.length === 0) return 'full';
  const hits = slots.filter(rs =>
    tutor.availability.some(ts => ts.day === rs.day && ts.timeOfDay === rs.timeOfDay)
  ).length;
  if (hits === slots.length) return 'full';
  if (hits > 0) return 'partial';
  return 'none';
}

// ── Component ─────────────────────────────────────────────────

const RequestTutorFlow: React.FC<RequestTutorFlowProps> = ({
  childName: initName = '',
  yearGroup: initYear,
  diagnosticFocusAreas = [],
  parentHasDistributor,
  tutors = MOCK_TUTORS,
  confirming = false,
  requestingMobile = false,
  onConfirm,
  onRequestMobile,
  onCancel,
}) => {
  // Navigation
  const [step, setStep] = useState<2 | 3>(2);

  // Step 1 (year group known from props)
  const [childName] = useState(initName);
  const [yearGroup] = useState<number | ''>(initYear ?? '');
  const [focusAreas] = useState<string[]>(diagnosticFocusAreas.slice(0, 3));

  // Step 2
  const [selectedDays, setSelectedDays] = useState<string[]>([]);
  const [selectedTimes, setSelectedTimes] = useState<TutorSlot['timeOfDay'][]>([]);
  const [frequency, setFrequency] = useState<TutorSelection['frequency'] | ''>('');
  const [err2, setErr2] = useState<{ days?: string; times?: string; freq?: string }>({});

  // Step 3
  const [sortBy, setSortBy] = useState<'best' | 'price' | 'rating'>('best');
  const [pendingTutor, setPendingTutor] = useState<Tutor | null>(null);
  const [bookableSlots, setBookableSlots] = useState<BookableSlot[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<BookableSlot | null>(null);
  const [slotErr, setSlotErr] = useState(false);

  useEffect(() => {
    if (!pendingTutor) { setBookableSlots([]); setSelectedSlot(null); return; }
    setSlotsLoading(true);
    apiFetch(`/api/tutors/${pendingTutor.id}/available_slots/`)
      .then(r => r.json())
      .then((data: BookableSlot[]) => setBookableSlots(data))
      .catch(() => setBookableSlots([]))
      .finally(() => setSlotsLoading(false));
  }, [pendingTutor]);

  const displayName = childName.trim() || 'your child';

  const toggleDay = useCallback((d: string) =>
    setSelectedDays(prev => prev.includes(d) ? prev.filter(x => x !== d) : [...prev, d]), []);

  const toggleTime = useCallback((t: TutorSlot['timeOfDay']) =>
    setSelectedTimes(prev => prev.includes(t) ? prev.filter(x => x !== t) : [...prev, t]), []);

  // ── Step 2 submit ──────────────────────────────────────────

  const submitStep2 = () => {
    const e: typeof err2 = {};
    if (!selectedDays.length) e.days = 'Please select at least one day.';
    if (!selectedTimes.length) e.times = 'Please select at least one time.';
    if (!frequency) e.freq = 'Please select how often.';
    if (Object.keys(e).length) { setErr2(e); return; }
    setErr2({});
    setStep(3);
  };

  // ── Tutor list ─────────────────────────────────────────────

  const requestedSlots = buildSlots(selectedDays, selectedTimes);

  const withQuality = tutors
    .map(t => ({ tutor: t, quality: matchQuality(t, requestedSlots) }))
    .filter(x => x.quality !== 'none') as { tutor: Tutor; quality: 'full' | 'partial' }[];

  const sorted = [...withQuality].sort((a, b) => {
    if (sortBy === 'price') return a.tutor.hourlyRate - b.tutor.hourlyRate;
    if (sortBy === 'rating') return (b.tutor.rating ?? -1) - (a.tutor.rating ?? -1);
    // best: full first, then by rating desc
    if (a.quality !== b.quality) return a.quality === 'full' ? -1 : 1;
    return (b.tutor.rating ?? -1) - (a.tutor.rating ?? -1);
  });

  // ── Confirm ────────────────────────────────────────────────

  const confirmSelection = () => {
    if (!pendingTutor || !yearGroup || !frequency) return;
    if (bookableSlots.length > 0 && !selectedSlot) {
      setSlotErr(true);
      return;
    }
    setSlotErr(false);
    onConfirm({
      tutor: pendingTutor,
      childName: childName.trim(),
      yearGroup: yearGroup as number,
      focusAreas: focusAreas.length ? focusAreas : ['General catch-up / multiple areas'],
      requestedDays: selectedSlot ? [selectedSlot.day] : selectedDays,
      requestedTimesOfDay: selectedSlot ? [] : selectedTimes,
      frequency: frequency as TutorSelection['frequency'],
      slot: selectedSlot ?? undefined,
    });
  };

  // ── Render ─────────────────────────────────────────────────

  const freqLabel = frequency === 'once' ? 'Once a week'
    : frequency === 'twice' ? 'Twice a week'
    : frequency === 'flexible' ? 'Flexible' : '';

  return (
    <div className="rtf-outer">
      <div className={step === 3 ? 'rtf-container--wide' : 'rtf-container'}>

        <StepIndicator currentStep={step - 1} steps={STEP_LABELS} />

        {/* ══════════════════════ STEP 2 ══════════════════════ */}
        {step === 2 && (
          <div>
            <h1 className="rtf-step-heading">
              When works best for {displayName}?
            </h1>

            {/* Days */}
            <div className="rtf-section">
              <span className="rtf-section-label">Days available</span>
              <div className="rtf-days">
                {DAYS.map(day => (
                  <button
                    key={day}
                    type="button"
                    className={`rtf-day-btn${selectedDays.includes(day) ? ' selected' : ''}`}
                    onClick={() => toggleDay(day)}
                  >
                    {day}
                  </button>
                ))}
              </div>
              {err2.days && <p className="rtf-field-error">{err2.days}</p>}
            </div>

            {/* Time of day */}
            <div className="rtf-section">
              <span className="rtf-section-label">Time of day</span>
              <div className="rtf-time-cards">
                {TIME_OPTIONS.map(({ value, icon, label }) => (
                  <div
                    key={value}
                    role="button"
                    tabIndex={0}
                    className={`rtf-time-card${selectedTimes.includes(value) ? ' selected' : ''}`}
                    onClick={() => toggleTime(value)}
                    onKeyDown={e => e.key === 'Enter' && toggleTime(value)}
                  >
                    <span className="rtf-time-card-icon">{icon}</span>
                    <div className="rtf-time-card-label">{label}</div>
                  </div>
                ))}
              </div>
              {err2.times && <p className="rtf-field-error">{err2.times}</p>}
            </div>

            {/* Frequency */}
            <div className="rtf-section">
              <span className="rtf-section-label">Session frequency</span>
              <div className="rtf-freq-cards">
                {FREQ_OPTIONS.map(({ value, label }) => (
                  <div
                    key={value}
                    role="button"
                    tabIndex={0}
                    className={`rtf-freq-card${frequency === value ? ' selected' : ''}`}
                    onClick={() => setFrequency(value)}
                    onKeyDown={e => e.key === 'Enter' && setFrequency(value)}
                  >
                    <span className="rtf-freq-card-text">{label}</span>
                  </div>
                ))}
              </div>
              {err2.freq && <p className="rtf-field-error">{err2.freq}</p>}
            </div>

            {/* Live summary sentence */}
            {buildSummary(selectedDays, selectedTimes, frequency) && (
              <div className="rtf-summary">
                {buildSummary(selectedDays, selectedTimes, frequency)}
              </div>
            )}

            <div className="rtf-actions">
              <button className="sm-btn-primary" onClick={submitStep2}>
                Show available tutors
              </button>
              {onCancel && <button className="sm-btn-ghost" onClick={onCancel}>Cancel</button>}
            </div>
          </div>
        )}

        {/* ══════════════════════ STEP 3 ══════════════════════ */}
        {step === 3 && (
          <div>
            {pendingTutor ? (
              /* ── Time picker panel ── */
              <div className="rtf-confirmation">
                <h1 className="rtf-confirmation-heading">
                  Choose a time with {pendingTutor.firstName} {pendingTutor.lastInitial}.
                </h1>
                <p className="rtf-confirmation-sub">
                  Select one of {pendingTutor.firstName}'s available times for{' '}
                  {childName.trim() || 'your child'}
                </p>

                {slotsLoading ? (
                  <p className="rtf-confirmation-sub">Loading available times…</p>
                ) : bookableSlots.length > 0 ? (
                  (() => {
                    const byDay = bookableSlots.reduce<Record<string, BookableSlot[]>>((acc, s) => {
                      (acc[s.dayFull] = acc[s.dayFull] || []).push(s);
                      return acc;
                    }, {});
                    return (
                      <div className="rtf-slot-days">
                        {Object.entries(byDay).map(([day, slots]) => (
                          <div key={day} className="rtf-slot-day-group">
                            <div className="rtf-slot-day-label">{day}</div>
                            <div className="rtf-slot-grid">
                              {slots.map(slot => {
                                const isSelected = selectedSlot?.day === slot.day && selectedSlot?.startTime === slot.startTime;
                                return (
                                  <div
                                    key={`${slot.day}-${slot.startTime}`}
                                    role="button"
                                    tabIndex={0}
                                    className={`rtf-slot-btn${isSelected ? ' selected' : ''}`}
                                    onClick={() => { setSelectedSlot(slot); setSlotErr(false); }}
                                    onKeyDown={e => e.key === 'Enter' && (setSelectedSlot(slot), setSlotErr(false))}
                                  >
                                    {formatTime(slot.startTime)}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                      </div>
                    );
                  })()
                ) : (
                  <p className="rtf-confirmation-sub">
                    No available times found — we'll be in touch to arrange a time.
                  </p>
                )}

                {slotErr && <p className="rtf-field-error">Please select a time to continue.</p>}

                <div className="rtf-actions">
                  <button className="sm-btn-primary" onClick={confirmSelection} disabled={confirming}>
                    {confirming ? 'Saving…' : 'Confirm first session'}
                  </button>
                  {onRequestMobile && (
                    <button
                      className="sm-btn-secondary"
                      onClick={() => onRequestMobile(pendingTutor.id)}
                      disabled={requestingMobile || confirming}
                    >
                      {requestingMobile ? 'Sending…' : `Request ${pendingTutor.firstName}'s mobile`}
                    </button>
                  )}
                  <button className="sm-btn-ghost" onClick={() => { setPendingTutor(null); setSelectedSlot(null); setBookableSlots([]); setSlotErr(false); }}>
                    ← Go back
                  </button>
                </div>
                <p className="rtf-consent-note">
                  By pressing Confirm first session you agree for your details to be sent to {pendingTutor.firstName} {pendingTutor.lastInitial}.
                </p>
              </div>
            ) : (
              /* ── Tutor list ── */
              <>
                <h1 className="rtf-step-heading">
                  Available tutors for {displayName}
                </h1>
                {scheduleLine(selectedDays, selectedTimes) && (
                  <p className="rtf-step-subheading">
                    Showing tutors who match your schedule —{' '}
                    {scheduleLine(selectedDays, selectedTimes)}
                  </p>
                )}

                <div className="rtf-sort-bar">
                  {(['best', 'price', 'rating'] as const).map(opt => (
                    <button
                      key={opt}
                      className={`rtf-sort-option${sortBy === opt ? ' active' : ''}`}
                      onClick={() => setSortBy(opt)}
                    >
                      {opt === 'best' ? 'Best match'
                        : opt === 'price' ? 'Lowest price'
                        : 'Highest rated'}
                    </button>
                  ))}
                </div>

                {tutors.length === 0 ? (
                  <div className="rtf-empty-state">
                    <h3>No tutors available</h3>
                    <p>We don't have any tutors available right now.</p>
                    <button className="sm-btn-primary" onClick={onCancel}>
                      Please call me to arrange a tutor
                    </button>
                  </div>
                ) : (
                  <>
                    {sorted.length === 0 && (
                      <div className="rtf-empty-state">
                        <p>No tutors match your exact schedule — showing all available tutors.</p>
                      </div>
                    )}
                    {(sorted.length > 0 ? sorted : tutors.map(t => ({ tutor: t, quality: 'partial' as const }))).map(({ tutor, quality }) => (
                      <TutorCard
                        key={tutor.id}
                        tutor={tutor}
                        requestedSlots={requestedSlots}
                        parentHasDistributor={parentHasDistributor}
                        matchQuality={quality}
                        onSelect={setPendingTutor}
                      />
                    ))}
                  </>
                )}

                <div className="rtf-actions">
                  <button className="sm-btn-ghost" onClick={() => setStep(2)}>
                    ← Adjust availability
                  </button>
                </div>
              </>
            )}
          </div>
        )}

      </div>
    </div>
  );
};

export default RequestTutorFlow;
