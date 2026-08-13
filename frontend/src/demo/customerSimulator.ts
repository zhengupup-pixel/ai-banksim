import type { Scenario } from "../types/training";

type Intent =
  | "greeting" | "identity" | "account" | "amount" | "purpose" | "materials"
  | "fee" | "duration" | "risk" | "authorization" | "loss" | "activation" | "confirmation" | "unknown";

const intentKeywords: Array<[Intent, string[]]> = [
  ["greeting", ["你好", "您好", "欢迎", "请问办理", "需要办理", "什么业务"]],
  ["identity", ["身份证", "证件", "身份", "本人", "名字", "姓名"]],
  ["account", ["账号", "账户", "卡号", "银行卡号", "收款人", "收款账户"]],
  ["amount", ["金额", "多少钱", "多少元", "存多少", "取多少", "转多少", "余额"]],
  ["purpose", ["用途", "为什么", "原因", "资金来源", "做什么", "干什么"]],
  ["materials", ["材料", "资料", "提供", "携带", "准备", "还需要"]],
  ["fee", ["手续费", "费用", "收费", "多少钱办理"]],
  ["duration", ["多久", "多长时间", "什么时候", "着急", "快点", "时间"]],
  ["risk", ["风险", "诈骗", "安全", "确认", "自愿", "提示"]],
  ["authorization", ["授权", "复核", "主管", "大额", "审核"]],
  ["loss", ["挂失", "丢", "遗失", "找不到", "冻结", "旧卡"]],
  ["activation", ["激活", "新卡", "补卡", "密码"]],
  ["confirmation", ["核对", "正确吗", "没问题", "确认一下", "是否正确"]],
];

const scenarioCopy: Record<string, Partial<Record<Intent, string>>> = {
  account_opening: {
    purpose: "我主要用这张卡接收生活费和日常消费，不用于出租、出借或买卖账户。",
    materials: "我带了本人身份证和手机，如果还需要补充职业或联系信息，我可以现场填写。",
    fee: "请问开户本身是否收费？如果有短信通知等可选服务，也请先告诉我费用。",
    risk: "我已了解不能出租、出借银行卡，也不会把验证码和密码告诉他人。",
    duration: "我今天时间比较充足，按正常流程办理就好。",
  },
  deposit: {
    purpose: "这笔现金是我的经营收入，来源正常，可以配合登记。",
    amount: "我今天要存入 68000 元，请帮我当面清点确认。",
    account: "存入我本人的 A001 账户，请您再帮我核对一次。",
    authorization: "可以，我理解大额现金需要复核，我会配合等待。",
    duration: "我稍后还有安排，麻烦告知大额复核大概需要多久。",
  },
  withdrawal: {
    purpose: "这笔钱用于家庭装修付款，是我本人真实意愿。",
    amount: "我要取 60000 元，账户余额足够，麻烦按大额取款流程办理。",
    authorization: "明白，大额取款需要主管授权，我愿意配合核验。",
    risk: "没有人通过电话或网络要求我取现，这次取款是我本人决定的。",
    duration: "我确实有点赶时间，但身份核验和授权步骤请正常办理。",
  },
  transfer: {
    purpose: "这笔款是支付合同款，我认识收款方，也核对过交易背景。",
    amount: "转账金额是 128000 元，请以柜面录入的信息为准。",
    account: "正确收款账户是 A002，请您在提交前再向我复述核对。",
    authorization: "可以，大额转账需要授权的话请按规定办理。",
    risk: "这是我本人发起的转账，没有陌生人催促，也不是所谓安全账户。",
  },
  loss_reporting: {
    loss: "卡片刚刚发现遗失，请立即正式挂失并冻结 C001，避免资金风险。",
    identity: "我是持卡人本人，证件号码是 ID001，可以配合身份核验。",
    materials: "我带了身份证，卡片已经找不到了，还需要提供哪些信息？",
    risk: "目前没有发现异常交易，请先冻结卡片；如果有可疑流水也请告诉我。",
    duration: "麻烦尽快完成冻结，我担心卡片被别人使用。",
  },
  card_replacement: {
    loss: "原卡已经电话挂失，挂失记录编号是 L001，请先确认旧卡状态。",
    activation: "新卡制作完成后我会本人设置密码并现场激活，也请确认旧卡不能再使用。",
    fee: "我知道补卡可能收取费用，请告知标准并给我回单。",
    materials: "我带了身份证，挂失记录编号是 L001，还需要补充什么资料？",
    duration: "请问新卡今天可以领取并激活吗？",
  },
};

function detectIntent(message: string): Intent {
  const normalized = message.trim().toLowerCase().replace(/[，。！？、,.!?\s]/g, "");
  let best: { intent: Intent; score: number } = { intent: "unknown", score: 0 };
  for (const [intent, words] of intentKeywords) {
    const score = words.reduce((total, word) => total + (normalized.includes(word) ? word.length : 0), 0);
    if (score > best.score) best = { intent, score };
  }
  return best.intent;
}

function factsFor(scenario: Scenario, intent: Intent): string | null {
  const facts = Object.entries(scenario.customer_profile.disclosed_facts);
  const preferred = intent === "identity" ? ["证件", "姓名"]
    : intent === "account" ? ["账户", "卡号", "收款"]
      : intent === "purpose" ? ["用途", "来源", "职业"]
        : intent === "loss" ? ["挂失", "卡"]
          : [];
  const matched = facts.filter(([key]) => preferred.some(word => key.includes(word)));
  const selected = matched.length ? matched : facts;
  if (!selected.length) return null;
  return selected.map(([key, value]) => `${key}是 ${value}`).join("，");
}

function fallbackReply(scenario: Scenario, message: string, turn: number): string {
  const variants = [
    `我想办理的是“${scenario.title}”。您可以告诉我现在需要核对哪一项信息吗？`,
    `好的，我会配合规范办理。关于您刚才说的“${message.slice(0, 18)}”，能否再具体说明一下？`,
    `我理解了。请继续按标准流程办理，需要身份、账户或用途信息时可以直接问我。`,
    `这方面我不太确定，麻烦您以柜面规则为准，并告诉我下一步需要做什么。`,
  ];
  const hash = [...message].reduce((sum, char) => sum + (char.codePointAt(0) ?? 0), 0);
  return variants[(hash + turn) % variants.length];
}

function varyWording(reply: string, turn: number): string {
  if (turn === 0) return reply;
  const prefixes = ["可以。", "好的，我补充说明一下：", "没问题。", "我确认一下："];
  return `${prefixes[(turn - 1) % prefixes.length]}${reply}`;
}

export function simulateCustomerReply(scenario: Scenario, message: string, turn = 0): string {
  const intent = detectIntent(message);
  const tailored = scenarioCopy[scenario.business_type]?.[intent];
  if (tailored) return varyWording(tailored, turn);

  if (intent === "greeting") return varyWording(`您好，我是${scenario.customer_profile.name}。${scenario.customer_profile.opening_line}`, turn);
  if (intent === "confirmation") return varyWording("请您把关键业务信息再复述一遍，我确认无误后再提交。", turn);

  const facts = intent === "identity" || intent === "account" || intent === "purpose" || intent === "loss"
    ? factsFor(scenario, intent)
    : null;
  if (facts) return varyWording(`好的，${facts}。请您按规定核验。`, turn);

  if (intent === "materials") return varyWording("我会配合提供办理所需资料，请您逐项说明，敏感信息我只在柜面核验时提供。", turn);
  if (intent === "fee") return varyWording("请先向我说明收费项目和标准，我确认后再办理。", turn);
  if (intent === "duration") return varyWording("我希望尽快办完，但必要的核验和风险步骤不能省略。", turn);
  if (intent === "risk") return varyWording("这是我本人自愿办理的业务，没有陌生人诱导；风险事项请您逐项提示。", turn);
  if (intent === "authorization") return varyWording("我理解复核和授权是必要的风险控制，请按规定办理。", turn);
  if (intent === "activation") return varyWording("请说明新卡激活和密码设置要求，我会本人操作。", turn);
  if (intent === "amount") return varyWording("请以业务资料中的金额为准，并在提交前与我再次核对。", turn);

  return fallbackReply(scenario, message, turn);
}
