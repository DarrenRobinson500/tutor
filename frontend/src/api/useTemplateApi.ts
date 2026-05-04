import { useState } from "react";
import { apiFetch, apiFetchJson } from "../utils/apiFetch"
import { TemplateSummary } from "../types/TemplateMetadata";

export function useTemplateApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function listTemplates(opts: {
    hasNotesOnly?: boolean;
    noSubjectOnly?: boolean;
    grade?: string;
    skill?: string;
    difficulty?: string;
    page?: number;
    pageSize?: number;
  } = {}): Promise<{ count: number; results: TemplateSummary[]; grade_options: string[]; skill_options: string[]; diff_options: string[] }> {
    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      if (opts.hasNotesOnly) params.set("has_notes", "true");
      if (opts.noSubjectOnly) params.set("no_skill_detail", "true");
      if (opts.grade)      params.set("grade", opts.grade);
      if (opts.skill)      params.set("skill", opts.skill);
      if (opts.difficulty) params.set("difficulty", opts.difficulty);
      if (opts.page && opts.page > 1) params.set("page", String(opts.page));
      if (opts.pageSize)   params.set("page_size", String(opts.pageSize));
      const url = params.toString() ? `/api/templates/?${params}` : "/api/templates/";
      const res = await apiFetch(url);
      if (!res.ok) throw new Error("Failed to load templates");
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      return { count: 0, results: [], grade_options: [], skill_options: [], diff_options: [] };
    } finally {
      setLoading(false);
    }
  }

  async function getTemplate(id: string) {
    setLoading(true);
    setError(null);

    try {
      const res = await apiFetch(`/api/templates/${id}/`);
      if (!res.ok) throw new Error("Failed to load template");
      return await res.json();
    } catch (err: any) {
      setError(err.message);
      return null;
    } finally {
      setLoading(false);
    }
  }


    async function saveTemplate(id: string | number, payload: any) {
      const isNew = id === "new";

      const url = isNew
        ? "/api/templates/"
        : `/api/templates/${id}/`;

      const method = isNew ? "POST" : "PUT";

      const res = await apiFetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      return res.ok ? await res.json() : null;
    }

    async function autosaveTemplate(id: number | string | null, content: string) {
      const res = await apiFetch("/api/templates/autosave/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, content }),
      });

      return res.ok ? await res.json() : { ok: false, status: res.status };

    }

    async function deleteTemplate(id: number) {
      await apiFetch(`/api/templates/${id}`, {
        method: "DELETE"
      });
    }

    function generateTemplate(skillId: number, grade: (string | number)): Promise<TemplateSummary> {
        return apiFetchJson("/api/templates/generate/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ skill_id: skillId, grade: grade }),
        });

    }

    async function getFirstTemplate(skillId: number, grade: string | number) {
      const params = new URLSearchParams({
        skill: String(skillId),
        grade: String(grade),
        difficulty: "Easy",
      });

      const res = await apiFetch(`/api/templates/filtered/?${params.toString()}`);
      if (!res.ok) return null;

      const list = await res.json();
      return list.length > 0 ? list[0] : null;
    }

//     async function saveDiagram(id: number, svg: string) {
//       return apiFetchJson(`/api/templates/${id}/diagram/`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ svg })
//       });
//     }



    return {
      listTemplates,
      getTemplate,
      saveTemplate,
      autosaveTemplate,
      deleteTemplate,
      generateTemplate,
      getFirstTemplate,
      loading,
      error,
    }
}