import axios from "axios";
import { getStoredAuth, getVisitorId, setVisitorId } from "./storage";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const visitorId = getVisitorId();
  if (visitorId) {
    config.headers["X-Visitor-Id"] = visitorId;
  }
  const auth = getStoredAuth();
  if (auth?.auth_user_id) {
    config.headers["X-Auth-User-Id"] = auth.auth_user_id;
  }
  return config;
});

api.interceptors.response.use((response) => {
  const visitorId = response?.data?.visitor_id;
  if (visitorId) {
    setVisitorId(visitorId);
  }
  return response;
});

export default api;
