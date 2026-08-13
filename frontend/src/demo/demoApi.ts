import type {
  AIEvaluation, AbilityAnalysis, AuthUser, CustomerMessageResponse, FinalTrainingReport,
  LoginResponse, RuleCheckResult, Scenario, ScenarioVersion, StoredTrainingReport,
  TrainingHistoryItem, TrainingPlan, TrainingSession
} from "../types/training";

type DemoSession = TrainingSession & { actions: string[]; started_at: string; report?: FinalTrainingReport };

const input = (name: string, label: string, input_type: "text" | "number" = "text") => ({ name, label, input_type, required: true });
const profile = (name: string, persona: string, opening_line: string, facts: Record<string, string | number>) => ({ name, persona, opening_line, disclosed_facts: facts });

export const demoUser: AuthUser = { id: 1, username: "competition_guest", display_name: "大赛体验官", role: "student" };

export const demoScenarios: Scenario[] = [
  {
    id: 1, title: "个人活期账户开户", business_type: "account_opening", difficulty: "基础",
    description: "接待首次独立办理银行业务的大学生，完成身份核验、资料收集与风险提示。",
    expected_steps: ["greet_customer", "verify_identity", "collect_documents", "risk_disclosure", "open_account", "confirm_receipt"], risk_rules: {},
    customer_profile: profile("陈晓雨", "对开户流程不熟悉的大学生", "你好，我想开一张平时生活费使用的银行卡。", { 证件号码: "ID001", 职业: "在校大学生" }),
    demo_inputs: { presented_id_number: "ID001", customer_id_number: "ID001" },
    rule_policy: { version: 1, enforce_step_order: true, inputs: [input("presented_id_number", "出示证件号码"), input("customer_id_number", "客户登记证件号码")], available_steps: [], conditional_steps: [], field_matches: [{ left_field: "presented_id_number", right_field: "customer_id_number", message: "出示证件与客户登记身份信息不匹配。" }] }
  },
  {
    id: 2, title: "个人现金存款", business_type: "deposit", difficulty: "基础",
    description: "办理本人账户现金存款；金额达到 5 万元时必须先完成大额现金复核。",
    expected_steps: ["greet_customer", "verify_account", "count_cash", "process_deposit", "confirm_receipt"], risk_rules: { large_cash_threshold: 50000 },
    customer_profile: profile("王建国", "重视效率、会询问复核原因", "你好，我要往自己的账户里存一笔现金。", { 账户: "A001", 资金来源: "经营收入" }),
    demo_inputs: { amount: 68000, account_number: "A001", customer_account_number: "A001" },
    rule_policy: { version: 1, enforce_step_order: true, inputs: [input("amount", "存款金额", "number"), input("account_number", "办理账户"), input("customer_account_number", "客户登记账户")], available_steps: ["large_cash_review"], conditional_steps: [{ field: "amount", operator: "gte", value: 50000, required_step: "large_cash_review", message: "大额现金存款缺少复核。", before_step: "process_deposit", order_message: "大额现金复核必须在存款入账前完成。" }], field_matches: [{ left_field: "account_number", right_field: "customer_account_number", message: "办理账户与客户登记账户不匹配。" }] }
  },
  {
    id: 3, title: "个人现金取款", business_type: "withdrawal", difficulty: "进阶",
    description: "核验客户身份与余额，识别大额取款并在出账前取得主管授权。",
    expected_steps: ["greet_customer", "verify_identity", "verify_account", "check_balance", "process_withdrawal", "count_cash", "confirm_receipt"], risk_rules: { large_cash_threshold: 50000 },
    customer_profile: profile("刘芳", "办理装修款取现、时间较紧", "你好，我今天想取一笔现金，时间有点赶。", { 证件号码: "ID001", 用途: "家庭装修" }),
    demo_inputs: { amount: 60000, account_balance: 120000, presented_id_number: "ID001", customer_id_number: "ID001" },
    rule_policy: { version: 1, enforce_step_order: true, inputs: [input("amount", "取款金额", "number"), input("account_balance", "账户余额", "number"), input("presented_id_number", "出示证件号码"), input("customer_id_number", "登记证件号码")], available_steps: ["authorize_large_withdrawal"], conditional_steps: [{ field: "amount", operator: "gte", value: 50000, required_step: "authorize_large_withdrawal", message: "大额取款缺少主管授权。", before_step: "process_withdrawal", order_message: "大额取款授权必须在出账前完成。" }], field_matches: [{ left_field: "presented_id_number", right_field: "customer_id_number", message: "取款人身份与账户登记身份不匹配。" }], balance_rules: [{ message: "取款金额超过账户可用余额。" }] }
  },
  {
    id: 4, title: "个人账户转账", business_type: "transfer", difficulty: "进阶",
    description: "核对付款人和收款信息，检查余额并识别大额转账授权要求。",
    expected_steps: ["greet_customer", "verify_identity", "verify_payer_account", "verify_recipient", "confirm_transfer_info", "process_transfer", "confirm_receipt"], risk_rules: { large_transfer_threshold: 100000 },
    customer_profile: profile("赵明", "转付合同款，容易报错账号末位", "你好，我需要从自己的账户转一笔合同款。", { 付款人证件: "ID001", 正确收款账户: "A002" }),
    demo_inputs: { amount: 128000, account_balance: 200000, payer_id_number: "ID001", account_owner_id_number: "ID001", recipient_account: "A002" },
    rule_policy: { version: 1, enforce_step_order: true, inputs: [input("amount", "转账金额", "number"), input("account_balance", "付款账户余额", "number"), input("payer_id_number", "付款人证件号码"), input("account_owner_id_number", "账户登记证件号码"), input("recipient_account", "收款账户")], available_steps: ["authorize_large_transfer"], conditional_steps: [{ field: "amount", operator: "gte", value: 100000, required_step: "authorize_large_transfer", message: "大额转账缺少主管授权。", before_step: "process_transfer", order_message: "大额转账授权必须在转账执行前完成。" }], field_matches: [{ left_field: "payer_id_number", right_field: "account_owner_id_number", message: "付款人身份与付款账户登记信息不匹配。" }], balance_rules: [{ message: "转账金额超过付款账户可用余额。" }] }
  },
  {
    id: 5, title: "银行卡挂失", business_type: "loss_reporting", difficulty: "基础",
    description: "安抚紧张客户，核验持卡关系并立即完成挂失和卡片冻结。",
    expected_steps: ["greet_customer", "verify_identity", "verify_card_ownership", "report_card_loss", "freeze_card", "confirm_receipt"], risk_rules: {},
    customer_profile: profile("孙悦", "刚发现银行卡遗失，担心资金风险", "我的银行卡找不到了，麻烦帮我尽快挂失。", { 银行卡号: "C001", 证件号码: "ID001" }),
    demo_inputs: { card_number: "C001", presented_id_number: "ID001", card_owner_id_number: "ID001" },
    rule_policy: { version: 1, enforce_step_order: true, inputs: [input("card_number", "银行卡号"), input("presented_id_number", "出示证件号码"), input("card_owner_id_number", "持卡人登记证件号码")], available_steps: [], conditional_steps: [], field_matches: [{ left_field: "presented_id_number", right_field: "card_owner_id_number", message: "申请人身份与持卡人登记身份不匹配。" }] }
  },
  {
    id: 6, title: "银行卡补卡", business_type: "card_replacement", difficulty: "进阶",
    description: "验证挂失记录、身份与补卡费用，完成新卡制作和激活。",
    expected_steps: ["greet_customer", "verify_identity", "verify_loss_report", "collect_replacement_fee", "replace_card", "activate_card", "confirm_receipt"], risk_rules: {},
    customer_profile: profile("周敏", "已电话挂失，关注费用和旧卡状态", "你好，我之前已经挂失了银行卡，今天来补一张新卡。", { 挂失记录编号: "L001", 证件号码: "ID001" }),
    demo_inputs: { loss_report_number: "L001", presented_id_number: "ID001", card_owner_id_number: "ID001", replacement_fee: 10 },
    rule_policy: { version: 1, enforce_step_order: true, inputs: [input("loss_report_number", "挂失记录编号"), input("presented_id_number", "出示证件号码"), input("card_owner_id_number", "持卡人登记证件号码"), input("replacement_fee", "补卡手续费", "number")], available_steps: [], conditional_steps: [], field_matches: [{ left_field: "presented_id_number", right_field: "card_owner_id_number", message: "补卡申请人身份与持卡人登记身份不匹配。" }] }
  }
];

let nextSessionId = 1;
let nextMessageId = 1;
const sessions = new Map<number, DemoSession>();

const scenarioFor = (session: DemoSession) => demoScenarios.find(item => item.id === session.scenario_id)!;
const applies = (value: unknown, operator: string, expected: string | number) => {
  if (operator === "gte") return Number(value) >= Number(expected);
  if (operator === "gt") return Number(value) > Number(expected);
  if (operator === "lte") return Number(value) <= Number(expected);
  if (operator === "lt") return Number(value) < Number(expected);
  return value === expected;
};

function evaluate(session: DemoSession, data: Record<string, string | number>): RuleCheckResult {
  const scenario = scenarioFor(session);
  const required = [...scenario.expected_steps];
  for (const condition of scenario.rule_policy.conditional_steps) {
    if (applies(data[condition.field], condition.operator, condition.value)) required.push(condition.required_step);
  }
  const missing = required.filter(step => !session.actions.includes(step));
  const violations: string[] = [];
  for (const field of scenario.rule_policy.inputs) {
    if (field.required && (data[field.name] === undefined || data[field.name] === "")) violations.push(`${field.label}为必填业务信息。`);
  }
  for (const match of scenario.rule_policy.field_matches ?? []) {
    if (data[match.left_field] !== data[match.right_field]) violations.push(match.message);
  }
  if (scenario.rule_policy.balance_rules?.length && Number(data.amount) > Number(data.account_balance)) violations.push(scenario.rule_policy.balance_rules[0].message);
  if (scenario.rule_policy.enforce_step_order) {
    const ordered = [...scenario.expected_steps];
    for (const condition of scenario.rule_policy.conditional_steps) {
      if (!applies(data[condition.field], condition.operator, condition.value) || !condition.before_step) continue;
      const authIndex = session.actions.indexOf(condition.required_step);
      const processIndex = session.actions.indexOf(condition.before_step);
      if (authIndex >= 0 && processIndex >= 0 && authIndex > processIndex) violations.push(condition.order_message ?? "授权步骤顺序错误。");
      const target = ordered.indexOf(condition.before_step);
      ordered.splice(target, 0, condition.required_step);
    }
    const performed = session.actions.filter(step => ordered.includes(step));
    for (let index = 1; index < performed.length; index += 1) {
      if (ordered.indexOf(performed[index]) < ordered.indexOf(performed[index - 1])) { violations.push("柜面操作顺序不符合标准流程。"); break; }
    }
  }
  const uniqueViolations = [...new Set(violations)];
  const score = Math.max(0, 100 - missing.length * 10 - uniqueViolations.length * 12);
  return { passed: missing.length === 0 && uniqueViolations.length === 0, score, missing_steps: missing, violations: uniqueViolations, suggestions: missing.length ? ["按标准顺序补齐缺失步骤后再次提交。"] : ["业务硬规则已满足，可进入最终评价。"] };
}

const history = (): TrainingHistoryItem[] => [...sessions.values()].map(session => {
  const scenario = scenarioFor(session); const report = session.report;
  return { session_id: session.id, scenario_id: scenario.id, scenario_title: scenario.title, business_type: scenario.business_type, difficulty: scenario.difficulty, status: session.status, started_at: session.started_at, completed_at: report?.completed_at ?? null, total_score: report?.total_score ?? null, rule_score: report?.rule_score ?? null, passed: report?.passed ?? null };
}).reverse();

const ability = (): AbilityAnalysis => {
  const completed = history().filter(item => item.status === "completed");
  const average = completed.length ? Math.round(completed.reduce((sum, item) => sum + (item.total_score ?? 0), 0) / completed.length) : 0;
  return { user_id: 1, completed_sessions: completed.length, average_score: average, pass_rate: completed.length ? Math.round(completed.filter(item => item.passed).length / completed.length * 100) : 0, business_abilities: completed.map(item => ({ business_type: item.business_type, scenario_title: item.scenario_title, completed_count: 1, average_score: item.total_score ?? 0, pass_rate: item.passed ? 100 : 0, level: (item.total_score ?? 0) >= 85 ? "proficient" : "developing" })), weaknesses: completed.flatMap(item => item.passed ? [] : [{ category: `${item.scenario_title}流程完整性`, count: 1 }]), recommended_business_types: completed.filter(item => !item.passed).map(item => item.business_type) };
};

export const demoApi = {
  health: async () => ({ status: "ok", service: "AI BankSim Competition Demo" }),
  seed: async () => ({ seeded: true }),
  login: async (): Promise<LoginResponse> => ({ access_token: "competition-demo", token_type: "bearer", expires_at: new Date(Date.now() + 86400000).toISOString(), user: demoUser }),
  me: async () => demoUser,
  logout: async () => undefined,
  scenarios: async () => demoScenarios,
  students: async () => [demoUser],
  updateScenario: async (_id: number, scenario: Scenario) => scenario,
  scenarioVersions: async (): Promise<ScenarioVersion[]> => [],
  trainingHistory: async () => history(),
  trainingReport: async (id: number): Promise<StoredTrainingReport> => { const session = sessions.get(id)!; const scenario = scenarioFor(session); return { ...session.report!, user_id: 1, scenario_id: scenario.id, scenario_title: scenario.title, business_type: scenario.business_type, difficulty: scenario.difficulty, started_at: session.started_at }; },
  abilityAnalysis: async () => ability(),
  conversations: async () => [],
  sendCustomerMessage: async (id: number, message: string): Promise<CustomerMessageResponse> => {
    const session = sessions.get(id)!; const scenario = scenarioFor(session); const now = new Date().toISOString();
    const lower = message.toLowerCase();
    const factText = Object.entries(scenario.customer_profile.disclosed_facts).map(([key, value]) => `${key}是${value}`).join("，");
    const reply = lower.includes("证件") || message.includes("信息") ? `好的，${factText}。请帮我按规范办理。` : lower.includes("用途") || message.includes("原因") ? "这是我本人正常办理的生活或经营业务，需要的话我可以配合说明资金用途。" : "好的，我会配合。请问接下来还需要我提供什么材料？";
    return { learner_message: { id: nextMessageId++, speaker: "learner", message, created_at: now }, customer_message: { id: nextMessageId++, speaker: "customer", message: reply, created_at: now }, ai_generated: false };
  },
  currentTrainingPlan: async () => demoPlan(),
  generateTrainingPlan: async () => demoPlan(),
  createSession: async (scenarioId: number): Promise<TrainingSession> => { const created: DemoSession = { id: nextSessionId++, user_id: 1, scenario_id: scenarioId, status: "active", context: {}, actions: [], started_at: new Date().toISOString() }; sessions.set(created.id, created); return created; },
  submitAction: async (id: number, action: string, data: Record<string, string | number>) => { const session = sessions.get(id)!; session.actions.push(action); session.context = { ...data }; return evaluate(session, data); },
  completeSession: async (id: number): Promise<FinalTrainingReport> => { const session = sessions.get(id)!; const check = evaluate(session, session.context as Record<string, string | number>); session.status = "completed"; const report: FinalTrainingReport = { session_id: id, status: "completed", completed_at: new Date().toISOString(), passed: check.passed, rule_score: check.score, total_score: check.score, missing_steps: check.missing_steps, violations: check.violations, suggestions: check.suggestions, examiner_report: check.passed ? "Examiner Agent：业务步骤完整、顺序正确，关键身份与金额规则均已满足。建议下一轮尝试更高风险等级场景。" : `Examiner Agent：本次确定性规则得分 ${check.score}。请重点补齐 ${check.missing_steps.length} 个步骤，并复核风险提示后重新训练。` }; session.report = report; return report; },
  askAgent: async (id: number, agentName: string): Promise<AIEvaluation> => { const session = sessions.get(id)!; const check = evaluate(session, session.context as Record<string, string | number>); return { agent_name: agentName, content: check.missing_steps.length ? `Coach Agent：下一步建议先完成“${check.missing_steps[0]}”。业务规则仍由确定性引擎判定。` : "Coach Agent：硬规则步骤已齐全，可以提交训练并查看 Examiner 最终解释。", metadata: { demo: true } }; }
};

function demoPlan(): TrainingPlan {
  const recommended = ability().recommended_business_types;
  const ordered = [...demoScenarios].sort((a, b) => Number(recommended.includes(b.business_type)) - Number(recommended.includes(a.business_type))).slice(0, 3);
  return { id: Date.now(), user_id: 1, title: "竞赛演示个性化训练计划", goals: ["掌握高风险柜面流程", "达到 85 分以上"], items: ordered.map((scenario, index) => ({ priority: index + 1, scenario_id: scenario.id, scenario_title: scenario.title, business_type: scenario.business_type, reason: index === 0 ? "根据当前薄弱项优先安排" : "覆盖尚未训练的核心业务", source: index === 0 && recommended.length ? "weak_business" : "untrained_business", current_average: null, target_score: 85 })), planner_explanation: "Planner Agent 根据确定性成绩与未训练业务排序；它只解释学习路径，不修改规则得分。", ai_generated: false, analysis_snapshot: ability(), recommendations: [], created_at: new Date().toISOString() };
}
