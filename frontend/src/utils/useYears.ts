import { useEffect, useState } from "react";
import { apiFetch } from "./apiFetch";

export interface Year {
  id: number;
  code: string;   // stored value: "K", "1", ..., "10", "11std", etc.
  label: string;  // display name: "Kindergarten", "Year 1", "Year 11 Standard", ...
  order: number;
  stage: string;  // "k10" or "s6"
}

let _cache: Year[] | null = null;
const _listeners: Array<(years: Year[]) => void> = [];

export function useYears() {
  const [years, setYears] = useState<Year[]>(_cache ?? []);

  useEffect(() => {
    if (_cache) {
      setYears(_cache);
      return;
    }
    _listeners.push(setYears);
    if (_listeners.length === 1) {
      // First subscriber — kick off the fetch
      apiFetch("/api/years/")
        .then(r => r.json())
        .then((data: Year[]) => {
          const years = Array.isArray(data) ? data : [];
          _cache = years;
          _listeners.forEach(fn => fn(years));
          _listeners.length = 0;
        })
        .catch(() => {});
    }
    return () => {
      const idx = _listeners.indexOf(setYears);
      if (idx !== -1) _listeners.splice(idx, 1);
    };
  }, []);

  return years;
}
