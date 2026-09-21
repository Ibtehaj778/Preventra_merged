const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

async function del(path) {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  getSummary:           ()       => get("/api/summary"),
  getGlobalSHAP:        ()       => get("/api/shap/global"),
  getPatients:          (params) => get("/api/patients?" + new URLSearchParams(params)),
  getPatient:           (id)     => get(`/api/patients/${id}`),
  getSegments:          ()       => get("/api/segments"),
  getSegment:           (id)     => get(`/api/segments/${id}`),
  getSurvival:          ()       => get("/api/survival"),
  getCostEffectiveness: ()       => get("/api/cost-effectiveness"),
  getBudgetImpact:      (body)   => post("/api/budget-impact", body),
  getModelInfo:         ()       => get("/api/model/info"),

  // Consequence Model (Phase 4 "Cost of Inaction" screen)
  getDownstreamCost:    ()       => get("/api/consequence/downstream-cost"),
  getReboundRisk:       ()       => get("/api/consequence/rebound-risk"),
  getPayerScenarios:    ()       => get("/api/consequence/payer-scenarios"),
  getPayerROI:          (interventionCost = 500, payerType = "current", adherenceUplift = 0.15) =>
    get(`/api/consequence/payer-roi?intervention_cost=${interventionCost}&payer_type=${payerType}&adherence_uplift=${adherenceUplift}`),

  // Chatbot
  postChatMessage:  (body)  => post("/api/chatbot/message", body),
  getChatSession:   (id)    => get(`/api/chatbot/session/${id}`),
  clearChatSession: (id)    => del(`/api/chatbot/session/${id}`),
  register: (body) => post("/api/auth/register", body),
  login: (body) => post("/api/auth/login", body),
};