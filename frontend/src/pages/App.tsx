import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, CheckCircle2, ChevronDown, FileCheck2, Landmark, MessageCircle, Play, Send, ShieldCheck } from "lucide-react";
import { api, isDemoMode, setAccessToken } from "../api/client";
import { demoUser } from "../demo/demoApi";
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

  const askCoach = useMutation({
    mutationFn: () => {
      if (!session) throw new Error("请先开始训练。");
      return api.askAgent(session.id, "coach", "请根据我当前训练表现给一个下一步提示。");
    },
    onSuccess: (response) => setAgentReply(response.content)
  });

  const submitAction = useMutation({
    mutationFn: (actionType: string) => {
      if (!session) throw new Error("请先开始训练。");
      return api.submitAction(session.id, actionType, businessData);
    },
    onSuccess: (check) => {
      setLatestCheck(check);
      askCoach.mutate();
    }
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

  const talkToCustomer = useMutation({
    mutationFn: (presetMessage?: string) => {
      if (!session) throw new Error("请先开始训练。");
      const message = presetMessage?.trim() || customerInput.trim();
      if (!message) throw new Error("请输入要对客户说的话。");
      return api.sendCustomerMessage(session.id, message);
    },
    onSuccess: (response) => {
      setConversation((current) => [...current, response.learner_message, response.customer_message]);
      setCustomerInput("");
    }
  });

  const isCompleted = session?.status === "completed";
  const canTrain = authUser?.role === "student";
  const mutationError = createSession.error ?? submitAction.error ?? askCoach.error ?? completeSession.error ?? talkToCustomer.error;

  const activeSteps = useMemo(
    () => {
      if (!selectedScenario) return [];
      const steps = [...selectedScenario.expected_steps];
      for (const conditional of selectedScenario.rule_policy.conditional_steps ?? []) {
        const actual = businessData[conditional.field];
        const expected = conditional.value;
        const applies = conditional.operator === "gte" ? Number(actual) >= Number(expected)
          : conditional.operator === "gt" ? Number(actual) > Number(expected)
            : conditional.operator === "lte" ? Number(actual) <= Number(expected)
              : conditional.operator === "lt" ? Number(actual) < Number(expected)
                : actual === expected;
        if (!applies) continue;
        const targetIndex = conditional.before_step ? steps.indexOf(conditional.before_step) : -1;
        steps.splice(targetIndex >= 0 ? targetIndex : steps.length, 0, conditional.required_step);
      }
      return steps;
    },
    [businessData, selectedScenario]
  );

  const completedSteps = useMemo(() => {
    if (!latestCheck) return [];
    return activeSteps.filter((step) => !latestCheck.missing_steps.includes(step));
  }, [activeSteps, latestCheck]);

  const nextStep = activeSteps.find((step) => !completedSteps.includes(step));
  const progress = activeSteps.length ? Math.round(completedSteps.length / activeSteps.length * 100) : 0;

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

      <section className="mx-auto max-w-4xl space-y-5 px-6 py-6">
          {isDemoMode && (
            <div className="flex items-center gap-3 border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
              <ShieldCheck size={18} className="shrink-0" />
              <span><strong>免登录比赛体验</strong> · 按引导完成业务，规则引擎评分，Agent 自动辅导。</span>
            </div>
          )}
          {mutationError && (
            <div className="border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {mutationError instanceof Error ? mutationError.message : "操作失败，请稍后重试。"}
            </div>
          )}
          <div className="panel p-6">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-end">
              <div className="min-w-0 flex-1">
                <label className="text-xs font-medium uppercase tracking-wide text-slate-400" htmlFor="scenario-select">选择训练场景</label>
              <select
                id="scenario-select"
                  className="mt-2 w-full border border-slate-200 bg-white px-3 py-3 text-sm font-medium text-ink outline-none focus:border-bank"
                value={selectedScenario?.id ?? ""}
                disabled={Boolean(session && !isCompleted)}
                onChange={(event) => chooseScenario(Number(event.target.value))}
              >
                {scenarios.data?.map((scenario) => (
                  <option key={scenario.id} value={scenario.id}>{scenario.title} · {scenario.difficulty}</option>
                ))}
              </select>
                <p className="mt-3 text-sm leading-6 text-slate-500">{selectedScenario?.description}</p>
              </div>
              <button
                className="inline-flex shrink-0 items-center justify-center gap-2 bg-bank px-6 py-3 text-sm font-medium text-white disabled:bg-slate-300"
                disabled={!selectedScenario || !canTrain || Boolean(session && !isCompleted) || createSession.isPending}
                onClick={() => selectedScenario && createSession.mutate(selectedScenario.id)}
              >
                <Play size={16} />
                {session && isCompleted ? "再练一次" : session ? "训练进行中" : "开始训练"}
              </button>
            </div>
          </div>

          {session && (
            <>
              <div className="panel p-6">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-400">训练进度</p>
                    <h2 className="mt-1 text-xl font-semibold text-ink">{isCompleted ? "训练完成" : nextStep ? `下一步：${stepLabels[nextStep] ?? nextStep}` : "流程已完成，可以提交"}</h2>
                  </div>
                  <div className="text-right"><p className="text-2xl font-semibold text-bank">{finalReport?.total_score ?? latestCheck?.score ?? progress}</p><p className="text-xs text-slate-400">{finalReport ? "最终得分" : latestCheck ? "当前得分" : "完成度"}</p></div>
                </div>
                <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-bank transition-all" style={{ width: `${progress}%` }} /></div>
                <div className="mt-5 flex flex-wrap gap-2">
                  {activeSteps.map((step, index) => {
                    const done = completedSteps.includes(step);
                    const current = step === nextStep;
                    return <span key={step} className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs ${done ? "bg-emerald-50 text-emerald-700" : current ? "bg-sky-50 text-bank" : "bg-slate-50 text-slate-400"}`}>{done ? <CheckCircle2 size={13} /> : <span>{index + 1}</span>}{stepLabels[step] ?? step}</span>;
                  })}
                </div>
              </div>

              <div className="panel p-6">
                <div className="flex items-center gap-2"><MessageCircle size={18} className="text-bank" /><h2 className="font-semibold text-ink">AI 客户 · {selectedScenario?.customer_profile.name}</h2></div>
                <div className="mt-4 space-y-3 bg-slate-50 p-4">
                  {conversation.length === 0 && <p className="text-sm leading-6 text-slate-600">“{selectedScenario?.customer_profile.opening_line}”</p>}
                  {conversation.slice(-2).map((message) => <p key={message.id} className={`text-sm leading-6 ${message.speaker === "learner" ? "text-right text-bank" : "text-slate-600"}`}>{message.message}</p>)}
                </div>
                {!isCompleted && conversation.length === 0 && <button className="mt-3 border border-bank px-4 py-2 text-sm text-bank" disabled={talkToCustomer.isPending} onClick={() => talkToCustomer.mutate("您好，我先核对您的业务需求和身份信息。")}>确认客户需求</button>}
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs text-slate-400">自由对话（可选）</summary>
                  <div className="mt-3 flex gap-2">
                  <input
                      className="min-w-0 flex-1 border border-slate-200 px-3 py-2 text-sm outline-none focus:border-bank"
                      placeholder="补充询问客户……" value={customerInput} disabled={isCompleted || talkToCustomer.isPending}
                      onChange={(event) => setCustomerInput(event.target.value)}
                      onKeyDown={(event) => { if (event.key === "Enter" && customerInput.trim()) talkToCustomer.mutate(undefined); }} />
                    <button className="bg-bank px-3 text-white disabled:bg-slate-300" disabled={isCompleted || !customerInput.trim() || talkToCustomer.isPending} onClick={() => talkToCustomer.mutate(undefined)} aria-label="发送消息"><Send size={15} /></button>
                  </div>
                </details>
              </div>

              <details className="panel p-6">
                <summary className="flex cursor-pointer list-none items-center justify-between font-semibold text-ink">业务资料已自动填写 <ChevronDown size={17} className="text-slate-400" /></summary>
                <p className="mt-2 text-sm text-slate-500">演示数据已准备好；展开可修改并测试规则异常。</p>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  {selectedScenario?.rule_policy.inputs.map((input) => <label key={input.name} className="text-sm text-slate-600"><span>{input.label}</span><input className="mt-2 w-full border border-slate-200 px-3 py-2 text-sm text-ink outline-none focus:border-bank disabled:bg-slate-50" type={input.input_type} min={input.minimum ?? undefined} max={input.maximum ?? undefined} value={businessData[input.name] ?? ""} disabled={isCompleted} onChange={(event) => updateBusinessData(input.name, event.target.value, input.input_type)} /></label>)}
                </div>
              </details>

              {!isCompleted && (
                <div className="panel border-bank p-6 text-center">
                  <p className="text-sm text-slate-500">{nextStep ? "系统已根据业务规则定位下一项标准操作" : "所有必要操作已完成"}</p>
                  {nextStep ? (
                    <button className="mt-4 inline-flex w-full items-center justify-center gap-2 bg-bank px-6 py-4 font-medium text-white disabled:bg-slate-300 sm:w-auto sm:min-w-72" disabled={submitAction.isPending} onClick={() => submitAction.mutate(nextStep)}><CheckCircle2 size={18} />{submitAction.isPending ? "规则检查中…" : `执行：${stepLabels[nextStep] ?? nextStep}`}</button>
                  ) : (
                    <button className="mt-4 inline-flex w-full items-center justify-center gap-2 bg-ink px-6 py-4 font-medium text-white disabled:bg-slate-300 sm:w-auto sm:min-w-72" disabled={completeSession.isPending} onClick={() => completeSession.mutate()}><FileCheck2 size={18} />{completeSession.isPending ? "生成报告中…" : "提交并生成最终报告"}</button>
                  )}
                  <div className="mx-auto mt-4 max-w-xl text-sm leading-6 text-slate-600"><span className="font-medium text-bank"><Bot size={15} className="mr-1 inline" />Coach Agent：</span>{agentReply || "开始操作后，我会自动解释下一步。"}</div>
                  {latestCheck?.violations.length ? <p className="mt-2 text-sm text-amber-700">规则提醒：{latestCheck.violations.join("；")}</p> : null}
                </div>
              )}
            </>
          )}

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

      </section>
    </main>
  );
}
