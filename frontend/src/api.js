const BASE = "/api";

export function getToken() {
  return localStorage.getItem("shecares_token");
}

export function setSession(access, refresh) {
  localStorage.setItem("shecares_token", access);
  if (refresh) localStorage.setItem("shecares_refresh", refresh);
}

export function clearSession() {
  localStorage.removeItem("shecares_token");
  localStorage.removeItem("shecares_refresh");
}

export function errorMessage(data) {
  if (!data) return "Something went wrong.";
  if (typeof data === "string") return data;
  if (data.detail) return Array.isArray(data.detail) ? data.detail.join(" ") : data.detail;
  return Object.entries(data)
    .map(([key, value]) => `${key}: ${[].concat(value).join(" ")}`)
    .join(" ");
}

let refreshing = null;

async function refreshAccess() {
  const refresh = localStorage.getItem("shecares_refresh");
  if (!refresh) return null;
  if (!refreshing) {
    refreshing = fetch(`${BASE}/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    })
      .then(async (res) => {
        if (!res.ok) return null;
        const data = await res.json();
        localStorage.setItem("shecares_token", data.access);
        return data.access;
      })
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

export async function api(path, options = {}, retried = false) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body = options.body;
  if (body && !(body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(`${BASE}${path}`, { method: options.method || "GET", headers, body });
  } catch {
    throw new Error("Cannot reach the server. Start the Django app on port 8000.");
  }
  if (response.status === 401 && !retried && !path.startsWith("/auth/")) {
    const renewed = await refreshAccess();
    if (renewed) return api(path, options, true);
    clearSession();
  }
  if (response.status === 204) return null;
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }
  if (!response.ok) {
    const error = new Error(errorMessage(data));
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

export async function downloadReport(id, filename) {
  const response = await fetch(`${BASE}/reports/${id}/download/`, {
    headers: { Authorization: `Bearer ${getToken()}` },
  });
  if (!response.ok) {
    let detail = "You cannot open this file.";
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {
      /* the file response is not JSON */
    }
    throw new Error(detail);
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || "report";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
