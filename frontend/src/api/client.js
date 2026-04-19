const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  analyzeText: (logContent, hint = "") =>
    request("/api/v1/analyze-log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ log_content: logContent, hint }),
    }),

  analyzeFile: (file, hint = "") => {
    const form = new FormData();
    form.append("file", file);
    if (hint) form.append("hint", hint);
    return request("/api/v1/upload-log", { method: "POST", body: form });
  },

  getHistory: (page = 1, pageSize = 20) =>
    request(`/api/v1/history?page=${page}&page_size=${pageSize}`),

  getSessionDetail: (sessionId) =>
    request(`/api/v1/history/${sessionId}`),
};
