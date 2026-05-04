import { create } from "zustand";
import { apiFetch } from "../utils/apiFetch";

interface PreferenceState {
  prefs: Record<string, any>;
  loaded: boolean;
  load: (prefs: Record<string, any>) => void;
  get: (key: string) => any;
  set: (key: string, value: any) => void;
}

export const usePreferenceStore = create<PreferenceState>((set, get) => ({
  prefs: {},
  loaded: false,

  load: (prefs) => set({ prefs, loaded: true }),

  get: (key) => get().prefs[key],

  set: (key, value) => {
    // Update local state immediately
    set((state) => ({
      prefs: { ...state.prefs, [key]: value }
    }));

    // Sync to backend
    apiFetch("/api/preferences/set/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value })
    });
  }
}));