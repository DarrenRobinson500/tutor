import { apiFetch } from "../utils/apiFetch"

export function usePreviewApi() {
  async function previewTemplate(data: { content: string }) {
    const res = await apiFetch("/api/templates/preview/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return await res.json();
  }

  return { previewTemplate };
}