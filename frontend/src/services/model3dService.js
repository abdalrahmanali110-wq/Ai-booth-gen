import api from "./api";

export async function createModel3D(sessionId, payload) {
  const { data } = await api.post(
    `/projects/${sessionId}/models3d`,
    payload,
    { timeout: 300000 }
  );
  return data;
}

export async function getModel3DJob(jobId) {
  const { data } = await api.get(`/models3d/${jobId}`);
  return data;
}

export async function processModel3DJob(jobId) {
  const { data } = await api.post(
    `/models3d/${jobId}/process`,
    {},
    { timeout: 300000 }
  );
  return data;
}
