export interface Segment {
  time: string;      // "09:00"
  type: string;      // "available" | "blocked" | "booked_other" | "outside" | etc.
  bookingId?: number;
}

export interface AvailabilityWindow {
  start: string;     // "09:00"
  end: string;       // "12:00"
}

export interface Booking {
  start: string;     // ISO datetime
  end: string;       // ISO datetime
  student: number;
}

export interface DayData {
  date: string;                     // "2026-02-03"
  availability: AvailabilityWindow[];
  blocked: boolean;
  bookings: Booking[];
  bookable_slots: string[];         // ["09:00", "11:15"]
  segments: Segment[];
}

export type WeekData = DayData[];

export interface Segment {
  time: string;
  type: string;
  bookingId?: number;
  studentName?: string;   // ⭐ add this
}
