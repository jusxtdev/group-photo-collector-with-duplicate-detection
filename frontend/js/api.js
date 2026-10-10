import { API_BASE, TOKEN_KEY } from "./config.js";

export class ApiError extends Error {
  constructor(message, { statusCode = 0, data = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.data = data;
  }
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthed() {
  return Boolean(getToken());
}

export function requireAuth() {
  if (!isAuthed()) {
    window.location.replace("index.html");
    return false;
  }
  return true;
}

export function redirectIfAuthed(target = "albums.html") {
  if (isAuthed()) {
    window.location.replace(target);
    return true;
  }
  return false;
}

export async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (auth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (err) {
    throw new ApiError("Could not reach the server", { statusCode: 0 });
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch (err) {
    payload = null;
  }

  if (response.status === 401 && auth) {
    clearToken();
    if (!window.location.pathname.endsWith("index.html") && window.location.pathname !== "/") {
      window.location.replace("index.html");
    }
  }

  if (payload && typeof payload === "object" && "status" in payload) {
    if (payload.status) {
      return payload.data;
    }
    throw new ApiError(payload.msg || "Request failed", {
      statusCode: response.status,
      data: payload.data,
    });
  }

  if (!response.ok) {
    throw new ApiError(`Request failed (${response.status})`, {
      statusCode: response.status,
    });
  }

  return payload;
}
