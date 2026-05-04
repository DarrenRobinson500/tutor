const API_URL = (process.env.REACT_APP_API_URL ?? "").replace(/\/$/, "");

// Shared refresh promise — prevents two concurrent 401s from each trying to
// refresh independently (which races and clears localStorage on the loser).
let _refreshPromise: Promise<string | null> | null = null;

async function getNewAccessToken(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    const refresh = localStorage.getItem("refresh");
    if (!refresh) {
      localStorage.removeItem("access");
      localStorage.removeItem("user");
      return null;
    }

    const res = await fetch(`${API_URL}/api/auth/jwt/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
      credentials: "include",
    });

    if (!res.ok) {
      localStorage.removeItem("access");
      localStorage.removeItem("refresh");
      localStorage.removeItem("user");
      return null;
    }

    const data = await res.json();
    localStorage.setItem("access", data.access);
    if (data.refresh) localStorage.setItem("refresh", data.refresh);
    return data.access as string;
  })().finally(() => { _refreshPromise = null; });

  return _refreshPromise;
}

export async function apiFetch(url: string, options: any = {}) {
  const fullUrl = `${API_URL}${url}`;

  const access = localStorage.getItem("access");

  const isFormData = options.body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
    ...(access ? { Authorization: `Bearer ${access}` } : {}),
  };

  const doFetch = (overrideHeaders = headers) =>
    fetch(fullUrl, { ...options, headers: overrideHeaders });

  // No token — unauthenticated request
  if (!access) return doFetch();

  let res = await doFetch();

  if (res.status === 401) {
    const newToken = await getNewAccessToken();
    if (!newToken) return res;

    res = await doFetch({
      ...headers,
      Authorization: `Bearer ${newToken}`,
    });
  }

  return res;
}

export async function apiFetchJson(url: string, options: any = {}) {
  const res = await apiFetch(url, options);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
