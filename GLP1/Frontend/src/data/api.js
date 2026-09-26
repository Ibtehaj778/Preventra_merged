import { endSession } from "../context/AuthContext";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// Accounts live in one place for both products: the Readmissions API's /auth/*
// endpoints, backed by `shared_identity.users`. This app never mints a token -
// it only receives one (from here, or from the portal on the URL fragment) and
// sends it back on protected calls. Keep this pointed at the auth service, not
// at VITE_API_URL.
export const AUTH_BASE = (import.meta.env.VITE_AUTH_URL ?? "http://localhost:8001").replace(/\/$/, "");

// Read straight from storage rather than from React state: this module is
// imported by hooks that run before any provider mounts, and AuthContext
// persists the token here on every sign-in and on the portal hand-off.
const TOKEN_KEY = "glp1_token";

/** Every /api route needs a bearer token signed by the auth service. */
function authHeaders(extra = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra;
}

/** 401 means the session is over: the token expired or the account was
 *  removed. End it here rather than let the caller fall back to mock data,
 *  which would show a signed-out user a dashboard of made-up numbers. */
function check(res, path) {
  if (res.status === 401) endSession();
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
}

async function get(path) {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders() });
  check(res, path);
  return res.json();
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  check(res, path);
  return res.json();
}

async function del(path) {
  const res = await fetch(`${BASE}${path}`, { method: "DELETE", headers: authHeaders() });
  check(res, path);
  return res.json();
}

/** The auth service answers on its own origin and needs no API key. */
async function authPost(path, body) {
  const res = await fetch(`${AUTH_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    // FastAPI puts the reason in `detail`; surfacing it is the difference
    // between "invalid email or password" and a blank "something went wrong".
    throw new Error(typeof data.detail === "string" ? data.detail : `Auth ${path} \u2192 ${res.status}`);
  }
  return normaliseSession(data);
}

/** The auth service speaks {token, user:{sub,...}}; this app speaks
 *  {access_token, user:{id,...}}. Translate once, here. */
function normaliseSession(data) {
  const u = data.user ?? {};
  return {
    access_token: data.token ?? data.access_token,
    user: {
      id:         u.sub ?? u.id,
      email:      u.email,
      role:       u.role,
      org_id:     u.org_id,
      org_name:   u.org_name,
      app_access: u.app_access ?? [],
    },
  };
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
  signup: (body) => authPost("/auth/signup", body),
  login:  (body) => authPost("/auth/login", body),
};