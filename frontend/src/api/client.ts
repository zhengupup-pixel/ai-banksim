import type { AIEvaluation, AbilityAnalysis, AuthUser, ConversationMessage, CustomerMessageResponse, FinalTrainingReport, LoginResponse, RuleCheckResult, Scenario, ScenarioVersion, StoredTrainingReport, TrainingHistoryItem, TrainingPlan, TrainingSession } from "../types/training";

const jsonHeaders = { "Content-Type": "application/json" };
const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${apiBaseUrl}${path}`, { ...options, headers });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; service: string }>("/api/health"),
  seed: () => request<{ seeded: boolean }>("/api/dev/seed", { method: "POST" }),
  login: (username: string, password: string) =>
    request<LoginResponse>("/api/auth/login", {
      method: "POST", headers: jsonHeaders, body: JSON.stringify({ username, password })
    }),
  me: () => request<AuthUser>("/api/auth/me"),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  scenarios: () => request<Scenario[]>("/api/scenarios"),
  students: () => request<AuthUser[]>("/api/students"),
  updateScenario: (scenarioId: number, scenario: Scenario) =>
    request<Scenario>(`/api/scenarios/${scenarioId}`, {
      method: "PUT", headers: jsonHeaders, body: JSON.stringify(scenario)
    }),
  scenarioVersions: (scenarioId: number) =>
    request<ScenarioVersion[]>(`/api/scenarios/${scenarioId}/versions`),
  trainingHistory: (userId?: number) =>
    request<TrainingHistoryItem[]>(`/api/training-sessions${userId ? `?user_id=${userId}` : ""}`),
  trainingReport: (sessionId: number) =>
    request<StoredTrainingReport>(`/api/training-sessions/${sessionId}/report`),
  abilityAnalysis: (userId?: number) =>
    request<AbilityAnalysis>(`/api/ability-analysis${userId ? `?user_id=${userId}` : ""}`),
  conversations: (sessionId: number) =>
    request<ConversationMessage[]>(`/api/training-sessions/${sessionId}/conversations`),
  sendCustomerMessage: (sessionId: number, message: string) =>
    request<CustomerMessageResponse>(`/api/training-sessions/${sessionId}/customer-messages`, {
      method: "POST", headers: jsonHeaders, body: JSON.stringify({ message })
    }),
  currentTrainingPlan: (userId?: number) =>
    request<TrainingPlan>(`/api/training-plans/current${userId ? `?user_id=${userId}` : ""}`),
  generateTrainingPlan: () =>
    request<TrainingPlan>("/api/training-plans/generate", { method: "POST" }),
  createSession: (scenarioId: number) =>
    request<TrainingSession>("/api/training-sessions", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ scenario_id: scenarioId })
    }),
  submitAction: (sessionId: number, actionType: string, payload: Record<string, string | number>) =>
    request<RuleCheckResult>(`/api/training-sessions/${sessionId}/actions`, {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ action_type: actionType, payload })
    }),
  completeSession: (sessionId: number) =>
    request<FinalTrainingReport>(`/api/training-sessions/${sessionId}/complete`, {
      method: "POST"
    }),
  askAgent: (sessionId: number, agentName: string, learnerMessage: string) =>
    request<AIEvaluation>("/api/ai/evaluate", {
      method: "POST",
      headers: jsonHeaders,
      body: JSON.stringify({ session_id: sessionId, agent_name: agentName, learner_message: learnerMessage })
    })
};
