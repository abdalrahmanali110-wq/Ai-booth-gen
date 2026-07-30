const VISITOR_KEY = "ai_booth_visitor_id";
const AUTH_KEY = "ai_booth_auth";
const PENDING_SESSION_KEY = "ai_booth_pending_session";
const PENDING_CONVERT_KEY = "ai_booth_pending_convert";

export function getVisitorId() {
  try {
    return localStorage.getItem(VISITOR_KEY) || null;
  } catch {
    return null;
  }
}

export function setVisitorId(id) {
  if (!id) return;
  try {
    localStorage.setItem(VISITOR_KEY, id);
  } catch {
    // ignore
  }
}

export function getStoredAuth() {
  try {
    const raw = localStorage.getItem(AUTH_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredAuth(auth) {
  try {
    if (!auth) {
      localStorage.removeItem(AUTH_KEY);
      return;
    }
    localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
  } catch {
    // ignore
  }
}

export function clearStoredAuth() {
  setStoredAuth(null);
}

export function setPendingAuthSession(sessionId) {
  try {
    if (sessionId) {
      sessionStorage.setItem(PENDING_SESSION_KEY, sessionId);
      sessionStorage.setItem(PENDING_CONVERT_KEY, "1");
    } else {
      sessionStorage.removeItem(PENDING_SESSION_KEY);
      sessionStorage.removeItem(PENDING_CONVERT_KEY);
    }
  } catch {
    // ignore
  }
}

export function getPendingAuthSession() {
  try {
    return sessionStorage.getItem(PENDING_SESSION_KEY);
  } catch {
    return null;
  }
}

export function consumePendingConvert() {
  try {
    const pending = sessionStorage.getItem(PENDING_CONVERT_KEY) === "1";
    sessionStorage.removeItem(PENDING_CONVERT_KEY);
    sessionStorage.removeItem(PENDING_SESSION_KEY);
    return pending;
  } catch {
    return false;
  }
}
