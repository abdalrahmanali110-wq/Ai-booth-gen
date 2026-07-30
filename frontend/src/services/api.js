import axios from "axios";
import { getVisitorId, setVisitorId } from "./storage";

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
