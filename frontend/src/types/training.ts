export type Scenario = {
  id: number;
  title: string;
  business_type: string;
  difficulty: string;
  description: string;
  expected_steps: string[];
  risk_rules: Record<string, unknown>;
  rule_policy: RulePolicy;
  customer_profile: CustomerProfile;
  demo_inputs?: Record<string, string | number>;
};

export type CustomerProfile = {
  name: string;
  persona: string;
  opening_line: string;
  disclosed_facts: Record<string, string | number>;
};

export type RuleInput = {
  name: string;
  label: string;
  input_type: "text" | "number";
  required: boolean;
  minimum?: number | null;
  maximum?: number | null;
};

export type RulePolicy = {
  version: 1;
  enforce_step_order: boolean;
  inputs: RuleInput[];
  available_steps: string[];
  conditional_steps: Array<{
    field: string;
    operator: "gte" | "gt" | "lte" | "lt" | "eq";
    value: number | string;
    required_step: string;
    message: string;
    before_step?: string | null;
    order_message?: string | null;
  }>;
  field_matches?: Array<{
    left_field: string;
    right_field: string;
    message: string;
  }>;
  balance_rules?: Array<{ message: string }>;
};

export type RuleCheckResult = {
  passed: boolean;
  score: number;
  missing_steps: string[];
  violations: string[];
  suggestions: string[];
};

export type TrainingSession = {
  id: number;
  user_id: number;
  scenario_id: number;
  status: string;
  context: Record<string, unknown>;
};

export type AIEvaluation = {
  agent_name: string;
  content: string;
  metadata: Record<string, unknown>;
};

export type FinalTrainingReport = {
  session_id: number;
  status: "completed";
  completed_at: string;
  passed: boolean;
  rule_score: number;
  total_score: number;
  missing_steps: string[];
  violations: string[];
  suggestions: string[];
  examiner_report: string;
};

export type AuthUser = {
  id: number;
  username: string;
  display_name: string;
  role: "student" | "teacher" | "admin";
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  user: AuthUser;
};

export type TrainingHistoryItem = {
  session_id: number;
  scenario_id: number;
  scenario_title: string;
  business_type: string;
  difficulty: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  total_score: number | null;
  rule_score: number | null;
  passed: boolean | null;
};

export type StoredTrainingReport = FinalTrainingReport & {
  user_id: number;
  scenario_id: number;
  scenario_title: string;
  business_type: string;
  difficulty: string;
  started_at: string;
};

export type AbilityAnalysis = {
  user_id: number;
  completed_sessions: number;
  average_score: number;
  pass_rate: number;
  business_abilities: Array<{
    business_type: string;
    scenario_title: string;
    completed_count: number;
    average_score: number;
    pass_rate: number;
    level: "proficient" | "competent" | "developing" | "needs_practice";
  }>;
  weaknesses: Array<{ category: string; count: number }>;
  recommended_business_types: string[];
};

export type ConversationMessage = {
  id: number;
  speaker: "learner" | "customer";
  message: string;
  created_at: string;
};

export type CustomerMessageResponse = {
  learner_message: ConversationMessage;
  customer_message: ConversationMessage;
  ai_generated: boolean;
};

export type TrainingPlan = {
  id: number;
  user_id: number;
  title: string;
  goals: string[];
  items: Array<{
    priority: number;
    scenario_id: number;
    scenario_title: string;
    business_type: string;
    reason: string;
    source: "weak_business" | "untrained_business" | "reinforcement";
    current_average: number | null;
    target_score: number;
  }>;
  planner_explanation: string;
  ai_generated: boolean;
  analysis_snapshot: Record<string, unknown>;
  recommendations: Array<{
    id: number;
    recommendation_type: string;
    content: string;
    priority: number;
  }>;
  created_at: string;
};

export type ScenarioVersion = {
  id: number;
  scenario_id: number;
  version_number: number;
  changed_by_user_id: number;
  snapshot: Record<string, unknown>;
  created_at: string;
};
