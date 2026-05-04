import { apiFetch } from "../utils/apiFetch"

export function useValidationApi() {
  async function validateTemplate(data: { content: string }) {
    const res = await apiFetch("/api/templates/validate/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    return await res.json();
  }

  return { validateTemplate };
}