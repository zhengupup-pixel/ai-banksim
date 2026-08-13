import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpenCheck, History, Landmark, Save, ShieldCheck, Users } from "lucide-react";
import { api } from "../api/client";
import type { AuthUser, Scenario } from "../types/training";


type Props = {
  user: AuthUser;
  onLogout: () => void;
};


export function TeacherDashboard({ user, onLogout }: Props) {
  const queryClient = useQueryClient();
  const [studentId, setStudentId] = useState<number | null>(null);
  const [scenarioId, setScenarioId] = useState<number | null>(null);
  const [draft, setDraft] = useState<Scenario | null>(null);

  const students = useQuery({ queryKey: ["students"], queryFn: api.students });
  const scenarios = useQuery({ queryKey: ["scenarios"], queryFn: api.scenarios });
  const selectedStudentId = studentId ?? students.data?.[0]?.id ?? null;
  const selectedScenario = scenarios.data?.find((item) => item.id === scenarioId) ?? scenarios.data?.[0] ?? null;

  useEffect(() => {
    if (selectedScenario) setDraft(structuredClone(selectedScenario));
  }, [selectedScenario]);

  const history = useQuery({
    queryKey: ["teacher-history", selectedStudentId],
    queryFn: () => api.trainingHistory(selectedStudentId ?? undefined),
    enabled: Boolean(selectedStudentId)
  });
  const ability = useQuery({
    queryKey: ["teacher-ability", selectedStudentId],
    queryFn: () => api.abilityAnalysis(selectedStudentId ?? undefined),
    enabled: Boolean(selectedStudentId)
  });
  const plan = useQuery({
    queryKey: ["teacher-plan", selectedStudentId],
    queryFn: () => api.currentTrainingPlan(selectedStudentId ?? undefined),
    enabled: Boolean(selectedStudentId), retry: false
  });
  const versions = useQuery({
    queryKey: ["scenario-versions", selectedScenario?.id],
    queryFn: () => api.scenarioVersions(selectedScenario!.id),
    enabled: Boolean(selectedScenario)
  });

  const saveScenario = useMutation({
    mutationFn: () => {
      if (!draft) throw new Error("没有可保存的场景。");
      return api.updateScenario(draft.id, draft);
    },
    onSuccess: (updated) => {
      queryClient.setQueryData<Scenario[]>(["scenarios"], (current) =>
        current?.map((item) => item.id === updated.id ? updated : item)
      );
      queryClient.invalidateQueries({ queryKey: ["scenario-versions", updated.id] });
    }
  });

  const selectedStudent = students.data?.find((item) => item.id === selectedStudentId);
  const completionSummary = useMemo(() => {
    const completed = history.data?.filter((item) => item.status === "completed") ?? [];
    return `${completed.length}/${history.data?.length ?? 0}`;
  }, [history.data]);

  return (
    <main className="min-h-screen bg-paper">
      <header className="sticky top-0 z-20 border-b border-slate-200/80 bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3"><div className="brand-mark"><Landmark size={21} /></div><div><h1 className="text-lg font-semibold text-ink">AI BankSim 教学工作台</h1><p className="text-xs text-slate-500">学生能力审阅 · 场景规则维护</p></div></div>
          <div className="flex items-center gap-3 text-sm text-slate-600"><ShieldCheck size={17} className="text-bank" /><span>{user.display_name} · {user.role}</span><button className="btn-ghost" onClick={onLogout}>退出</button></div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-5 py-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="space-y-5">
          <div className="panel">
            <div className="section-title"><Users size={18} /><div><h2>学生训练审阅</h2><p>选择学生查看确定性成绩、薄弱项与训练计划</p></div></div>
            <select className="field mt-4" value={selectedStudentId ?? ""} onChange={(event) => setStudentId(Number(event.target.value))}>
              {students.data?.map((student) => <option key={student.id} value={student.id}>{student.display_name} · {student.username}</option>)}
            </select>
            <div className="mt-4 grid grid-cols-3 gap-3">
              <TeacherMetric label="完成/全部" value={completionSummary} />
              <TeacherMetric label="平均分" value={ability.data?.average_score ?? 0} />
              <TeacherMetric label="通过率" value={`${ability.data?.pass_rate ?? 0}%`} />
            </div>
            <div className="mt-5 space-y-3">
              {ability.data?.business_abilities.map((item) => <div key={item.business_type}><div className="flex justify-between text-xs text-slate-500"><span>{item.scenario_title}</span><span>{item.average_score} · {item.level}</span></div><div className="progress-track mt-1"><div className="progress-fill" style={{ width: `${Math.min(item.average_score, 100)}%` }} /></div></div>)}
              {!ability.data?.business_abilities.length && <p className="empty-copy">{selectedStudent?.display_name ?? "该学生"}尚无已完成训练。</p>}
            </div>
          </div>

          <div className="panel">
            <div className="section-title"><History size={18} /><div><h2>近期记录与计划</h2><p>规则成绩与 Planner 推荐均保留历史</p></div></div>
            <div className="mt-4 space-y-2">
              {history.data?.slice(0, 6).map((item) => <div key={item.session_id} className="review-row"><div><p>{item.scenario_title}</p><span>{new Date(item.started_at).toLocaleDateString()} · {item.status}</span></div><strong className={item.passed ? "text-emerald-700" : "text-amber-700"}>{item.total_score ?? "--"}</strong></div>)}
            </div>
            {plan.data && <div className="mt-4 rounded-xl bg-teal-50 p-4"><p className="text-xs font-semibold uppercase tracking-wider text-bank">当前训练计划</p>{plan.data.items.map((item) => <p key={item.priority} className="mt-2 text-sm text-slate-700">{item.priority}. {item.scenario_title} · 目标 {item.target_score}</p>)}</div>}
          </div>
        </section>

        <section className="space-y-5">
          <div className="panel">
            <div className="section-title"><BookOpenCheck size={18} /><div><h2>训练场景管理</h2><p>保存前由服务端验证规则策略，并自动记录旧版本快照</p></div></div>
            <select className="field mt-4" value={selectedScenario?.id ?? ""} onChange={(event) => setScenarioId(Number(event.target.value))}>{scenarios.data?.map((scenario) => <option key={scenario.id} value={scenario.id}>{scenario.title}</option>)}</select>
            {draft && <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <label className="field-label sm:col-span-2">场景标题<input className="field mt-2" value={draft.title} onChange={(event) => setDraft({ ...draft, title: event.target.value })} /></label>
              <label className="field-label">难度<select className="field mt-2" value={draft.difficulty} onChange={(event) => setDraft({ ...draft, difficulty: event.target.value })}><option value="basic">basic</option><option value="intermediate">intermediate</option><option value="advanced">advanced</option></select></label>
              <label className="field-label">客户姓名<input className="field mt-2" value={draft.customer_profile.name} onChange={(event) => setDraft({ ...draft, customer_profile: { ...draft.customer_profile, name: event.target.value } })} /></label>
              <label className="field-label sm:col-span-2">场景说明<textarea className="field mt-2 min-h-24" value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} /></label>
              <label className="field-label sm:col-span-2">客户画像<textarea className="field mt-2 min-h-20" value={draft.customer_profile.persona} onChange={(event) => setDraft({ ...draft, customer_profile: { ...draft.customer_profile, persona: event.target.value } })} /></label>
              <label className="field-label sm:col-span-2">客户开场白<textarea className="field mt-2 min-h-20" value={draft.customer_profile.opening_line} onChange={(event) => setDraft({ ...draft, customer_profile: { ...draft.customer_profile, opening_line: event.target.value } })} /></label>
              <div className="sm:col-span-2 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-6 text-slate-600">规则策略 v{draft.rule_policy.version} · 必做步骤 {draft.expected_steps.length} 项 · 动态输入 {draft.rule_policy.inputs.length} 项。结构化规则仍由后端验证，AI 不参与规则裁决。</div>
              <button className="btn-primary sm:col-span-2" disabled={saveScenario.isPending} onClick={() => saveScenario.mutate()}><Save size={15} />{saveScenario.isPending ? "保存中" : "保存并创建版本"}</button>
            </div>}
          </div>

          <div className="panel">
            <div className="section-title"><History size={18} /><div><h2>场景版本记录</h2><p>每次编辑保存修改前的完整快照</p></div></div>
            <div className="mt-4 space-y-2">{versions.data?.map((item) => <div key={item.id} className="review-row"><div><p>版本 {item.version_number}</p><span>{new Date(item.created_at).toLocaleString()} · 操作用户 #{item.changed_by_user_id}</span></div><span className="text-xs text-slate-500">{String(item.snapshot.title ?? "历史场景")}</span></div>)}{!versions.data?.length && <p className="empty-copy">尚无编辑版本，首次保存后会产生记录。</p>}</div>
          </div>
        </section>
      </div>
    </main>
  );
}


function TeacherMetric({ label, value }: { label: string; value: string | number }) {
  return <div className="metric-card"><p>{label}</p><strong>{value}</strong></div>;
}
