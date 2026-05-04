import { useState } from "react";
import { apiFetchJson } from "../utils/apiFetch"


export interface Skill {
  id: number;
  parent: number | null;
  code: string;
  description: string;
  grade_level: number;
  order_index: number;
  children_count?: number;
  template_count: number;
  detail_covered: number;
  detail_total: number;
}

export function useSkillsApi() {
// eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [loading] = useState(false);
// eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [error, setError] = useState<string | null>(null);

  function listSkills(parent: number | null = null): Promise<Skill[]> {
    const url = parent
      ? `/api/skills/?parent=${parent}`
      : `/api/skills/`;
    return apiFetchJson(url);
  }

  function getSkill(id: number): Promise<Skill> {
    return apiFetchJson(`/api/skills/${id}/`);
  }

  function createSkill(payload: Partial<Skill>): Promise<Skill> {
    return apiFetchJson(`/api/skills/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  }

  function getParents(id: number): Promise<Skill[]> {
    return apiFetchJson(`/api/skills/${id}/parents/`);
  }


  function deleteSkill(id: number): Promise<void> {
    return apiFetchJson(`/api/skills/${id}/`, { method: "DELETE" });
  }

  function loadSyllabus(): Promise<any> {
      return apiFetchJson("/api/skills/load_syllabus/", {
        method: "POST",
      });
    }


  return {
    listSkills,
    getSkill,
    createSkill,
    deleteSkill,
    getParents,
    loadSyllabus,
    loading,
    error,
  };
}