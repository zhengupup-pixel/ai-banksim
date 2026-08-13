import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, CalendarRange, CheckCircle2, FileCheck2, History, Landmark, MessageCircle, Play, RefreshCw, Send, ShieldCheck, TrendingUp } from "lucide-react";
import { api, isDemoMode, setAccessToken } from "../api/client";
import { demoUser } from "../demo/demoApi";
import { Metric } from "../components/Metric";
import { TeacherDashboard } from "./TeacherDashboard";
import type { AuthUser, ConversationMessage, FinalTrainingReport, RuleCheckResult, TrainingSession } from "../types/training";

const stepLabels: Record<string, string> = {
  greet_customer: "迎接客户",
  verify_identity: "身份核验",
  collect_documents: "资料收集",
  risk_disclosure: "风险提示",
  open_account: "账户开立",
  confirm_receipt: "回单确认",
  verify_account: "账户核验",
  count_cash: "现金清点",
  process_deposit: "办理存款",
  check_balance: "余额检查",
  process_withdrawal: "办理取款",
  authorize_large_withdrawal: "大额取款授权",
  large_cash_review: "大额现金复核",
  verify_payer_account: "付款账户核验",
  verify_recipient: "收款人核验",
  confirm_transfer_info: "转账信息确认",
  process_transfer: "办理转账",
  authorize_large_transfer: "大额转账授权",
  verify_card_ownership: "持卡关系核验",
  report_card_loss: "登记挂失",
  freeze_card: "冻结卡片",
  verify_loss_report: "挂失记录核验",
  collect_replacement_fee: "收取补卡费用",
  replace_card: "制作新卡",
  activate_card: "激活新卡"
};

export function App() {
  const queryClient = useQueryClient();
  const [authUser, setAuthUser] = useState<AuthUser | null>(isDemoMode ? demoUser : null);
  const [username, setUsername] = useState("demo_student");
  const [password, setPassword] = useState("Student123!");
  const [loginError, setLoginError] = useState("");
  const [session, setSession] = useState<TrainingSession | null>(null);
  const [latestCheck, setLatestCheck] = useState<RuleCheckResult | null>(null);
  const [agentReply, setAgentReply] = useState("");
  const [finalReport, setFinalReport] = useState<FinalTrainingReport | null>(null);
  const [selectedScenarioId, setSelectedScenarioId] = useState<number | null>(null);
  const [businessData, setBusinessData] = useState<Record<string, string | number>>({});
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [customerInput, setCustomerInput] = useState("");

  const scenarios = useQuery({
    queryKey: ["scenarios"],
    queryFn: async () => {
      return api.scenarios();
    },
    enabled: Boolean(authUser)
  });

  const history = useQuery({
    queryKey: ["training-history", authUser?.id],
    queryFn: () => api.trainingHistory(),
    enabled: authUser?.role === "student"
  });

  const ability = useQuery({
    queryKey: ["ability-analysis", authUser?.id],
    queryFn: () => api.abilityAnalysis(),
    enabled: authUser?.role === "student"
  });

  const trainingPlan = useQuery({
    queryKey: ["training-plan", authUser?.id],
    queryFn: () => api.currentTrainingPlan(),
    enabled: authUser?.role === "student",
    retry: false
  });

  const login = useMutation({
    mutationFn: () => api.login(username, password),
    onSuccess: (response) => {
      setAccessToken(response.access_token);
      setAuthUser(response.user);
      setLoginError("");
    },
    onError: () => setLoginError("用户名或密码错误。")
  });

  const logout = async () => {
    if (isDemoMode) return;
    try { await api.logout(); } finally {
      setAccessToken(null);
      setAuthUser(null);
      setSession(null);
    }
  };

  const selectedScenario = scenarios.data?.find((scenario) => scenario.id === selectedScenarioId) ?? scenarios.data?.[0];

  const createSession = useMutation({
    mutationFn: (scenarioId: number) => api.createSession(scenarioId),
    onSuccess: (created) => {
      setSession(created);
      setLatestCheck(null);
      setAgentReply("");
      setFinalReport(null);
      setBusinessData(selectedScenario?.demo_inputs ?? {});
      setConversation([]);
      setCustomerInput("");
      queryClient.invalidateQueries({ queryKey: ["training-history"] });
    }
  });

  const submitAction = useMutation({
    mutationFn: (actionType: string) => {
      if (!session) throw new Error("请先开始训练。");
      return api.submitAction(session.id, actionType, businessData);
    },
    onSuccess: setLatestCheck
  });

  const askCoach = useMutation({
    mutationFn: () => {
      if (!session) throw new Error("请先开始训练。");
      return api.askAgent(session.id, "coach", "请根据我当前训练表现给一个下一步提示。");
    },
    onSuccess: (response) => setAgentReply(response.content)
  });

  const completeSession = useMutation({
    mutationFn: () => {
      if (!session) throw new Error("请先开始训练。");
      return api.completeSession(session.id);
    },
    onSuccess: (report) => {
      setFinalReport(report);
      setSession((current) => (current ? { ...current, status: report.status } : current));
      queryClient.invalidateQueries({ queryKey: ["training-history"] });
      queryClient.invalidateQueries({ queryKey: ["ability-analysis"] });
    }
  });

  const loadReport = useMutation({
    mutationFn: (sessionId: number) => api.trainingReport(sessionId),
    onSuccess: (report) => setFinalReport(report)
  });

  const talkToCustomer = useMutation({
    mutationFn: () => {
      if (!session) throw new Error("请先开始训练。");
      if (!customerInput.trim()) throw new Error("请输入要对客户说的话。");
      return api.sendCustomerMessage(session.id, customerInput.trim());
    },
    onSuccess: (response) => {
      setConversation((current) => [...current, response.learner_message, response.customer_message]);
      setCustomerInput("");
    }
  });

  const generatePlan = useMutation({
    mutationFn: () => api.generateTrainingPlan(),
    onSuccess: (plan) => queryClient.setQueryData(["training-plan", authUser?.id], plan)
  });

  const isCompleted = session?.status === "completed";
  const canTrain = authUser?.role === "student";
  const mutationError = createSession.error ?? submitAction.error ?? askCoach.error ?? completeSession.error ?? loadReport.error ?? talkToCustomer.error ?? generatePlan.error;

  const completedCount = useMemo(() => {
    if (!selectedScenario || !latestCheck) return 0;
    return selectedScenario.expected_steps.filter((step) => !latestCheck.missing_steps.includes(step)).length;
  }, [latestCheck, selectedScenario]);

  const allSteps = useMemo(
    () => {
      if (!selectedScenario) return [];
      const steps = [...selectedScenario.expected_steps];
      for (const conditional of selectedScenario.rule_policy.conditional_steps ?? []) {
        const targetIndex = conditional.before_step ? steps.indexOf(conditional.before_step) : -1;
        steps.splice(targetIndex >= 0 ? targetIndex : steps.length, 0, conditional.required_step);
      }
      for (const availableStep of selectedScenario.rule_policy.available_steps ?? []) {
        if (!steps.includes(availableStep)) steps.push(availableStep);
      }
      return steps;
    },
    [selectedScenario]
  );

  const chooseScenario = (scenarioId: number) => {
    setSelectedScenarioId(scenarioId);
    setSession(null);
    setLatestCheck(null);
    setFinalReport(null);
    setAgentReply("");
    setBusinessData({});
    setConversation([]);
    setCustomerInput("");
  };

  const updateBusinessData = (name: string, value: string, inputType: "text" | "number") => {
    setBusinessData((current) => ({
      ...current,
      [name]: inputType === "number" && value !== "" ? Number(value) : value
    }));
  };

  if (!authUser) {
    return (
      <main className="flex min-h-screen items-center justify-center px-6 py-12">
        <div className="panel w-full max-w-md p-8">
          <div className="flex items-center gap-3">
            <div className="brand-mark"><Landmark size={22} /></div>
            <div><h1 className="text-xl font-semibold text-ink">AI BankSim</h1><p className="text-sm text-slate-500">登录银行柜员训练平台</p></div>
          </div>
          <div className="mt-7 space-y-4">
            <label className="field-label block">用户名<input className="field mt-2" value={username} onChange={(event) => setUsername(event.target.value)} /></label>
            <label className="field-label block">密码<input type="password" className="field mt-2" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            {loginError && <p className="text-sm text-red-600">{loginError}</p>}
            <button className="btn-primary w-full disabled:bg-slate-300" disabled={login.isPending} onClick={() => login.mutate()}>{login.isPending ? "登录中" : "进入训练平台"}</button>
          </div>
          <p className="mt-5 text-xs leading-5 text-slate-400">本地演示账号已预填。生产环境必须关闭开发种子接口。</p>
        </div>
      </main>
    );
  }

  if (authUser.role !== "student") {
    return <TeacherDashboard user={authUser} onLogout={logout} />;
  }

  return (
    <main className="min-h-screen">
      <section className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="brand-mark">
              <Landmark size={22} />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-ink">AI BankSim</h1>
              <p className="text-sm text-slate-500">智能银行柜员综合训练平台</p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <ShieldCheck size={18} className="text-bank" />
            <span>{authUser.display_name} · {isDemoMode ? "免登录竞赛演示" : authUser.role}</span>
            {!isDemoMode && <button className="btn-ghost ml-3 py-1" onClick={logout}>退出</button>}
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-5 px-6 py-6 lg:grid-cols-[1.3fr_0.7fr]">
        <div className="space-y-5">
          {isDemoMode && (
            <div className="border border-sky-200 bg-sky-50 px-4 py-3 text-sm leading-6 text-sky-800">
              <strong>Agent 产品比赛演示模式</strong>：无需账号，训练数据仅保留在当前页面。规则评分由浏览器内确定性引擎执行；客户、教练与考官响应为可复现演示，真实 DeepSeek Provider 保留在服务端源码中。
            </div>
          )}
          {mutationError && (
            <div className="border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {mutationError instanceof Error ? mutationError.message : "操作失败，请稍后重试。"}
            </div>
          )}
          <div className="panel">
            <div className="mb-5">
              <label className="text-xs font-medium uppercase tracking-wide text-slate-400" htmlFor="scenario-select">训练场景</label>
              <select
                id="scenario-select"
                className="mt-2 w-full border border-slate-200 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-bank"
                value={selectedScenario?.id ?? ""}
                disabled={Boolean(session && !isCompleted)}
                onChange={(event) => chooseScenario(Number(event.target.value))}
              >
                {scenarios.data?.map((scenario) => (
                  <option key={scenario.id} value={scenario.id}>{scenario.title} · {scenario.difficulty}</option>
                ))}
              </select>
            </div>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-ink">{selectedScenario?.title ?? "加载场景中"}</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{selectedScenario?.description}</p>
              </div>
              <button
                className="inline-flex items-center gap-2 bg-bank px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
                disabled={!selectedScenario || !canTrain || createSession.isPending}
                onClick={() => selectedScenario && createSession.mutate(selectedScenario.id)}
              >
                <Play size={16} />
                {canTrain ? "开始训练" : "仅学生可训练"}
              </button>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <Metric label={finalReport ? "最终分数" : "当前分数"} value={finalReport ? `${finalReport.total_score}` : latestCheck ? `${latestCheck.score}` : "--"} />
            <Metric label="已完成步骤" value={selectedScenario ? `${completedCount}/${selectedScenario.expected_steps.length}` : "--"} />
            <Metric label="训练状态" value={isCompleted ? "已完成" : session ? "进行中" : "未开始"} />
          </div>

          <div className="panel">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-2"><MessageCircle size={18} className="text-bank" /><h2 className="text-base font-semibold text-ink">AI 客户 · {selectedScenario?.customer_profile.name}</h2></div>
              <span className="text-xs text-slate-400">{selectedScenario?.customer_profile.persona}</span>
            </div>
            <div className="mt-4 max-h-72 space-y-3 overflow-y-auto bg-slate-50 p-4">
              {conversation.length === 0 && <div className="max-w-[85%] bg-white px-3 py-2 text-sm leading-6 text-slate-600">{selectedScenario?.customer_profile.opening_line}</div>}
              {conversation.map((message) => (
                <div key={message.id} className={`flex ${message.speaker === "learner" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] px-3 py-2 text-sm leading-6 ${message.speaker === "learner" ? "bg-bank text-white" : "bg-white text-slate-600"}`}>{message.message}</div>
                </div>
              ))}
            </div>
            <div className="mt-3 flex gap-2">
              <input
                className="min-w-0 flex-1 border border-slate-200 px-3 py-2 text-sm outline-none focus:border-bank disabled:bg-slate-50"
                placeholder="以柜员身份与客户沟通……"
                value={customerInput}
                disabled={!session || isCompleted || talkToCustomer.isPending}
                onChange={(event) => setCustomerInput(event.target.value)}
                onKeyDown={(event) => { if (event.key === "Enter" && customerInput.trim()) talkToCustomer.mutate(); }}
              />
              <button className="inline-flex items-center gap-2 bg-bank px-4 py-2 text-sm text-white disabled:bg-slate-300" disabled={!session || isCompleted || !customerInput.trim() || talkToCustomer.isPending} onClick={() => talkToCustomer.mutate()}><Send size={15} />发送</button>
            </div>
            <p className="mt-2 text-xs text-slate-400">客户对话用于情景模拟和解释上下文，不会改变规则引擎判定。</p>
          </div>

          <div className="panel">
            <h2 className="text-base font-semibold text-ink">业务信息</h2>
            <p className="mt-1 text-sm text-slate-500">规则引擎将使用这些字段核验金额、余额和客户身份。</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {selectedScenario?.rule_policy.inputs.map((input) => (
                <label key={input.name} className="text-sm text-slate-600">
                  <span>{input.label}{input.required ? " *" : ""}</span>
                  <input
                    className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm text-ink outline-none focus:border-bank disabled:bg-slate-50"
                    type={input.input_type}
                    min={input.minimum ?? undefined}
                    max={input.maximum ?? undefined}
                    value={businessData[input.name] ?? ""}
                    disabled={!session || isCompleted}
                    onChange={(event) => updateBusinessData(input.name, event.target.value, input.input_type)}
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="panel">
            <h2 className="text-base font-semibold text-ink">柜面操作</h2>
            <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {allSteps.map((step) => (
                <button
                  key={step}
                  className="flex items-center justify-between border border-slate-200 px-4 py-3 text-left text-sm hover:border-bank disabled:bg-slate-50 disabled:text-slate-400"
                  disabled={!session || isCompleted || submitAction.isPending}
                  onClick={() => submitAction.mutate(step)}
                >
                  <span>{stepLabels[step] ?? step}</span>
                  <CheckCircle2 size={16} className="text-bank" />
                </button>
              ))}
            </div>
            <div className="mt-5 flex justify-end border-t border-slate-100 pt-4">
              <button
                className="inline-flex items-center gap-2 bg-ink px-4 py-2 text-sm font-medium text-white disabled:bg-slate-300"
                disabled={!session || isCompleted || completeSession.isPending}
                onClick={() => completeSession.mutate()}
              >
                <FileCheck2 size={16} />
                {completeSession.isPending ? "生成报告中" : "完成并提交训练"}
              </button>
            </div>
          </div>

          {finalReport && (
            <div className="panel border-bank">
              <div className="flex items-center justify-between gap-4">
                <h2 className="text-base font-semibold text-ink">最终训练报告</h2>
                <span className={`px-3 py-1 text-sm font-medium ${finalReport.passed ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>
                  {finalReport.passed ? "规则检查通过" : "规则检查未通过"}
                </span>
              </div>
              <div className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-2">
                <p>规则分：<span className="font-semibold text-ink">{finalReport.rule_score}</span></p>
                <p>最终分：<span className="font-semibold text-ink">{finalReport.total_score}</span></p>
                <p>缺失步骤：{finalReport.missing_steps.map((step) => stepLabels[step] ?? step).join("、") || "无"}</p>
                <p>风险违规：{finalReport.violations.join("、") || "无"}</p>
              </div>
              <div className="mt-4 border-t border-slate-100 pt-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Examiner Agent 评价解释</p>
                <p className="mt-2 text-sm leading-6 text-slate-600">{finalReport.examiner_report}</p>
              </div>
            </div>
          )}

          {canTrain && (
            <div className="panel">
              <div className="flex items-center gap-2"><History size={18} className="text-bank" /><h2 className="text-base font-semibold text-ink">训练历史</h2></div>
              <div className="mt-4 space-y-3">
                {!history.data?.length && <p className="text-sm text-slate-500">暂无训练记录。</p>}
                {history.data?.slice(0, 8).map((item) => (
                  <div key={item.session_id} className="flex items-center justify-between gap-4 border-b border-slate-100 pb-3 text-sm last:border-0">
                    <div>
                      <p className="font-medium text-ink">{item.scenario_title}</p>
                      <p className="mt-1 text-xs text-slate-400">{new Date(item.started_at).toLocaleString()} · {item.status === "completed" ? "已完成" : "进行中"}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={item.passed === true ? "text-emerald-700" : item.passed === false ? "text-amber-700" : "text-slate-400"}>{item.total_score ?? "--"} 分</span>
                      {item.status === "completed" && <button className="border border-slate-200 px-3 py-1 text-bank hover:border-bank" onClick={() => loadReport.mutate(item.session_id)}>查看报告</button>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <aside className="space-y-5">
          {canTrain && (
            <div className="panel">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2"><CalendarRange size={18} className="text-bank" /><h2 className="text-base font-semibold text-ink">下一步训练计划</h2></div>
                <button className="inline-flex items-center gap-1 border border-slate-200 px-2 py-1 text-xs text-bank hover:border-bank disabled:text-slate-300" disabled={generatePlan.isPending} onClick={() => generatePlan.mutate()}><RefreshCw size={13} />{trainingPlan.data ? "重新生成" : "生成计划"}</button>
              </div>
              {!trainingPlan.data && <p className="mt-3 text-sm leading-6 text-slate-500">根据确定性成绩与薄弱项生成下一轮训练顺序。</p>}
              {trainingPlan.data && (
                <>
                  <div className="mt-4 space-y-3">
                    {trainingPlan.data.items.map((item) => (
                      <button key={`${trainingPlan.data.id}-${item.priority}`} className="w-full border border-slate-100 p-3 text-left hover:border-bank" onClick={() => chooseScenario(item.scenario_id)}>
                        <div className="flex items-center justify-between text-sm"><span className="font-medium text-ink">{item.priority}. {item.scenario_title}</span><span className="text-bank">目标 {item.target_score}</span></div>
                        <p className="mt-1 text-xs leading-5 text-slate-500">{item.reason}</p>
                      </button>
                    ))}
                  </div>
                  <div className="mt-4 border-t border-slate-100 pt-3"><p className="text-xs font-medium text-slate-400">PlannerAgent 解释</p><p className="mt-2 text-xs leading-5 text-slate-600">{trainingPlan.data.planner_explanation}</p></div>
                </>
              )}
            </div>
          )}
          {canTrain && ability.data && (
            <div className="panel">
              <div className="flex items-center gap-2"><TrendingUp size={18} className="text-bank" /><h2 className="text-base font-semibold text-ink">能力分析</h2></div>
              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                <div className="bg-slate-50 p-2"><p className="text-lg font-semibold text-ink">{ability.data.completed_sessions}</p><p className="text-xs text-slate-400">完成次数</p></div>
                <div className="bg-slate-50 p-2"><p className="text-lg font-semibold text-ink">{ability.data.average_score}</p><p className="text-xs text-slate-400">平均分</p></div>
                <div className="bg-slate-50 p-2"><p className="text-lg font-semibold text-ink">{ability.data.pass_rate}%</p><p className="text-xs text-slate-400">通过率</p></div>
              </div>
              <div className="mt-4 space-y-3">
                {ability.data.business_abilities.map((item) => (
                  <div key={item.business_type}>
                    <div className="flex justify-between text-xs text-slate-500"><span>{item.scenario_title}</span><span>{item.average_score}</span></div>
                    <div className="mt-1 h-2 bg-slate-100"><div className="h-2 bg-bank" style={{ width: `${Math.min(item.average_score, 100)}%` }} /></div>
                  </div>
                ))}
              </div>
              {ability.data.weaknesses.length > 0 && <div className="mt-4 border-t border-slate-100 pt-3"><p className="text-xs font-medium text-slate-400">主要薄弱项</p>{ability.data.weaknesses.slice(0, 3).map((item) => <p key={item.category} className="mt-2 text-xs leading-5 text-slate-600">{item.category} × {item.count}</p>)}</div>}
            </div>
          )}
          <div className="panel">
            <h2 className="text-base font-semibold text-ink">规则检查</h2>
            <div className="mt-3 text-sm leading-6 text-slate-600">
              {!latestCheck && "提交一次柜面操作后，这里会显示确定性业务规则检查结果。"}
              {latestCheck && (
                <>
                  <p>{latestCheck.passed ? "流程已满足当前规则。" : "流程仍有缺失或风险。"}</p>
                  <p>缺失步骤：{latestCheck.missing_steps.map((step) => stepLabels[step] ?? step).join("、") || "无"}</p>
                  <p>风险违规：{latestCheck.violations.join("、") || "无"}</p>
                </>
              )}
            </div>
          </div>

          <div className="panel">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-ink">AI 教练</h2>
              <button
                className="inline-flex items-center gap-2 border border-bank px-3 py-2 text-sm font-medium text-bank disabled:border-slate-200 disabled:text-slate-400"
                disabled={!session || isCompleted || askCoach.isPending}
                onClick={() => askCoach.mutate()}
              >
                <Bot size={16} />
                获取提示
              </button>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600">{agentReply || (isDemoMode ? "点击获取可复现的 Coach Agent 演示提示；服务端版本可安全切换 DeepSeekProvider。" : "AI 教练已接入 MockProvider，可通过后端环境变量切换 DeepSeekProvider。")}</p>
          </div>
        </aside>
      </section>
    </main>
  );
}
