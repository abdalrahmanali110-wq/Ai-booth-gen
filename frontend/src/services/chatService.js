import api from "./api";

export async function listSessions() {
  const { data } = await api.get("/chat/sessions");
  return data;
}

export async function createSession(title = "New Booth Consultation") {
  const { data } = await api.post("/chat/session", { title });
  return data;
}

export async function sendMessage(sessionId, message) {
  const { data } = await api.post(
    "/chat/message",
    {
      session_id: sessionId,
      message,
    },
    {
      timeout: 180000,
    }
  );
  return data;
}

export async function getSession(sessionId) {
  const { data } = await api.get(`/chat/session/${sessionId}`);
  return data;
}

export async function getMessages(sessionId) {
  const { data } = await api.get(`/chat/session/${sessionId}/messages`);
  return data;
}

export async function generateBooth(sessionId) {
  const { data } = await api.post(
    `/chat/session/${sessionId}/generate`,
    {},
    {
      timeout: 180000,
    }
  );
  return data;
}

export async function updateSession(sessionId, title) {
  const { data } = await api.patch(`/chat/session/${sessionId}`, { title });
  return data;
}

export async function deleteSession(sessionId) {
  const { data } = await api.delete(`/chat/session/${sessionId}`);
  return data;
}
