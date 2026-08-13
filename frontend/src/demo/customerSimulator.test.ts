import { describe, expect, it } from "vitest";
import { demoScenarios } from "./demoApi";
import { simulateCustomerReply } from "./customerSimulator";

describe("competition customer simulator", () => {
  it("returns distinct, scenario-grounded replies for different intents", () => {
    const opening = demoScenarios[0];
    const identity = simulateCustomerReply(opening, "请出示您的身份证件");
    const purpose = simulateCustomerReply(opening, "请问这张卡主要用于什么用途？");
    const fee = simulateCustomerReply(opening, "办理这个业务会收费吗？");

    expect(new Set([identity, purpose, fee]).size).toBe(3);
    expect(identity).toContain("ID001");
    expect(purpose).toContain("生活费");
    expect(fee).toContain("费用");
  });

  it("uses business-specific facts across scenarios", () => {
    const deposit = demoScenarios.find(item => item.business_type === "deposit")!;
    const transfer = demoScenarios.find(item => item.business_type === "transfer")!;

    expect(simulateCustomerReply(deposit, "这笔钱的资金来源是什么？")).toContain("经营收入");
    expect(simulateCustomerReply(transfer, "请核对一下收款账号")).toContain("A002");
  });

  it("varies fallback replies using message content and conversation turn", () => {
    const opening = demoScenarios[0];
    const first = simulateCustomerReply(opening, "今天天气不错", 0);
    const second = simulateCustomerReply(opening, "今天天气不错", 1);

    expect(first).not.toBe(second);
    expect(first.length).toBeGreaterThan(10);
  });

  it("varies wording when the same intent is asked repeatedly", () => {
    const opening = demoScenarios[0];
    const first = simulateCustomerReply(opening, "请说明开户用途", 0);
    const second = simulateCustomerReply(opening, "这张卡准备做什么", 1);

    expect(first).not.toBe(second);
    expect(first).toContain("生活费");
    expect(second).toContain("生活费");
  });
});
