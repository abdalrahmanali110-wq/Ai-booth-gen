import api from "./api";

export async function getAuthConfig() {
  const { data } = await api.get("/auth/config");
  return data;
}

export async function completeOAuth(payload) {
  const { data } = await api.post("/auth/oauth/complete", payload);
  return data;
}

export async function claimSession(sessionId, payload) {
  const { data } = await api.post(`/projects/${sessionId}/claim`, payload);
  return data;
}
