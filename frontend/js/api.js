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

// Reads the current user's ID from the JWT `sub` claim.
// The API contract documents `sub` as the user ID string; there is no /me endpoint.
export function getCurrentUserId() {
  const token = getToken();
  if (!token) return null;
  const payload = token.split(".")[1];
  if (!payload) return null;
  try {
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(
      base64.length + ((4 - (base64.length % 4)) % 4),
      "=",
    );
    const claims = JSON.parse(atob(padded));
    return claims.sub != null ? String(claims.sub) : null;
  } catch (err) {
    return null;
  }
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
  // multipart/form-data bodies (photo upload) must let the browser set the
  // Content-Type so it can include the multipart boundary.
  const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
  if (body !== undefined && !isFormData) {
    headers["Content-Type"] = "application/json";
  }
  if (auth) {
    const token = getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  let requestBody;
  if (body !== undefined) {
    requestBody = isFormData ? body : JSON.stringify(body);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: requestBody,
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
