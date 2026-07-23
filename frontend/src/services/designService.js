import api from "./api";

export async function getQuestions() {
  const { data } = await api.get("/design/questions");
  return data;
}

export async function createDesignSession(title = "Booth Design") {
  const { data } = await api.post("/design/session", { title });
  return data;
}

export async function getDesignSession(sessionId) {
  const { data } = await api.get(`/design/session/${sessionId}`);
  return data;
}

export async function listDesignSessions() {
  const { data } = await api.get("/design/sessions");
  return data;
}

export async function saveAnswers(sessionId, answers) {
  const { data } = await api.patch(`/design/session/${sessionId}/answers`, {
    answers,
  });
  return data;
}

export async function generateDesign(sessionId) {
  const { data } = await api.post(
    `/design/session/${sessionId}/generate`,
    {},
    { timeout: 180000 }
  );
  return data;
}

export async function regenerateDesign(sessionId) {
  const { data } = await api.post(
    `/design/session/${sessionId}/regenerate`,
    {},
    { timeout: 180000 }
  );
  return data;
}

export async function submitLead(sessionId, contact) {
  const { data } = await api.post(`/design/session/${sessionId}/lead`, contact);
  return data;
}
