from typing import Any


DEMO_SCENARIOS: list[dict[str, Any]] = [
    {
        "id": 1,
        "title": "个人活期账户开户",
        "business_type": "account_opening",
        "difficulty": "basic",
        "description": "客户携带身份证到网点办理个人活期账户开户。",
        "customer_profile": {
            "name": "陈晓雨", "persona": "第一次独立办理银行业务，礼貌但对开户流程不熟悉。",
            "opening_line": "你好，我想开一张平时生活费使用的银行卡。",
            "disclosed_facts": {"证件号码": "ID001", "职业": "在校大学生"},
            "internal_notes": ["只有柜员询问时才说明开户用途", "不会替柜员判断合规步骤"],
        },
        "expected_steps": [
            "greet_customer", "verify_identity", "collect_documents",
            "risk_disclosure", "open_account", "confirm_receipt",
        ],
        "risk_rules": {},
        "scoring_policy": {"rule_weight": 0.8, "ai_weight": 0.2},
        "rule_policy": {
            "version": 1,
            "enforce_step_order": True,
            "inputs": [
                {"name": "presented_id_number", "label": "出示证件号码"},
                {"name": "customer_id_number", "label": "客户登记证件号码"},
            ],
            "field_matches": [{
                "left_field": "presented_id_number",
                "right_field": "customer_id_number",
                "message": "出示证件与客户登记身份信息不匹配。",
            }],
        },
    },
    {
        "id": 2,
        "title": "个人现金存款",
        "business_type": "deposit",
        "difficulty": "basic",
        "description": "客户向本人账户存入现金，大额现金需完成复核。",
        "customer_profile": {
            "name": "王建国", "persona": "携带现金来存款，重视办理速度，会询问大额业务为何需要复核。",
            "opening_line": "你好，我要往自己的账户里存一笔现金。",
            "disclosed_facts": {"账户": "A001", "资金来源": "经营收入"},
            "internal_notes": ["金额由学员在业务信息中确认", "被问到资金来源时如实回答"],
        },
        "expected_steps": [
            "greet_customer", "verify_account", "count_cash",
            "process_deposit", "confirm_receipt",
        ],
        "risk_rules": {"large_cash_threshold": 50000},
        "scoring_policy": {"rule_weight": 0.8, "ai_weight": 0.2},
        "rule_policy": {
            "version": 1,
            "enforce_step_order": True,
            "inputs": [
                {"name": "amount", "label": "存款金额", "input_type": "number", "minimum": 0.01},
                {"name": "account_number", "label": "办理账户"},
                {"name": "customer_account_number", "label": "客户登记账户"},
            ],
            "field_matches": [{
                "left_field": "account_number", "right_field": "customer_account_number",
                "message": "办理账户与客户登记账户不匹配。",
            }],
            "conditional_steps": [{
                "field": "amount", "operator": "gte", "value": 50000,
                "required_step": "large_cash_review", "message": "大额现金存款缺少复核。",
                "before_step": "process_deposit", "order_message": "大额现金复核必须在存款入账前完成。",
            }],
            "available_steps": ["large_cash_review"],
        },
    },
    {
        "id": 3,
        "title": "个人现金取款",
        "business_type": "withdrawal",
        "difficulty": "intermediate",
        "description": "客户办理现金取款，需核验身份、余额及大额授权。",
        "customer_profile": {
            "name": "刘芳", "persona": "准备支付装修款，取款金额较大，对等待授权略显焦急。",
            "opening_line": "你好，我今天想取一笔现金，时间有点赶。",
            "disclosed_facts": {"证件号码": "ID001", "取款用途": "家庭装修"},
            "internal_notes": ["不得要求柜员跳过身份核验", "询问时解释大额取款用途"],
        },
        "expected_steps": [
            "greet_customer", "verify_identity", "verify_account", "check_balance",
            "process_withdrawal", "count_cash", "confirm_receipt",
        ],
        "risk_rules": {"large_cash_threshold": 50000},
        "scoring_policy": {"rule_weight": 0.8, "ai_weight": 0.2},
        "rule_policy": {
            "version": 1,
            "enforce_step_order": True,
            "inputs": [
                {"name": "amount", "label": "取款金额", "input_type": "number", "minimum": 0.01},
                {"name": "account_balance", "label": "账户余额", "input_type": "number", "minimum": 0},
                {"name": "presented_id_number", "label": "出示证件号码"},
                {"name": "customer_id_number", "label": "客户登记证件号码"},
            ],
            "field_matches": [{
                "left_field": "presented_id_number", "right_field": "customer_id_number",
                "message": "取款人身份与账户登记身份不匹配。",
            }],
            "balance_rules": [{"message": "取款金额超过账户可用余额。"}],
            "conditional_steps": [{
                "field": "amount", "operator": "gte", "value": 50000,
                "required_step": "authorize_large_withdrawal", "message": "大额取款缺少主管授权。",
                "before_step": "process_withdrawal", "order_message": "大额取款授权必须在出账前完成。",
            }],
            "available_steps": ["authorize_large_withdrawal"],
        },
    },
    {
        "id": 4,
        "title": "个人账户转账",
        "business_type": "transfer",
        "difficulty": "intermediate",
        "description": "客户发起账户转账，需核对付款人、收款账户、余额及风险授权。",
        "customer_profile": {
            "name": "赵明", "persona": "需要转付合同款，带齐材料，但容易报错收款账号末位。",
            "opening_line": "你好，我需要从自己的账户转一笔合同款。",
            "disclosed_facts": {"付款人证件": "ID001", "正确收款账户": "A002"},
            "internal_notes": ["首次口述账号时提醒柜员再次核对", "不得确认未复述的转账信息"],
        },
        "expected_steps": [
            "greet_customer", "verify_identity", "verify_payer_account",
            "verify_recipient", "confirm_transfer_info", "process_transfer", "confirm_receipt",
        ],
        "risk_rules": {"large_transfer_threshold": 100000},
        "scoring_policy": {"rule_weight": 0.8, "ai_weight": 0.2},
        "rule_policy": {
            "version": 1,
            "enforce_step_order": True,
            "inputs": [
                {"name": "amount", "label": "转账金额", "input_type": "number", "minimum": 0.01},
                {"name": "account_balance", "label": "付款账户余额", "input_type": "number", "minimum": 0},
                {"name": "payer_id_number", "label": "付款人证件号码"},
                {"name": "account_owner_id_number", "label": "账户登记证件号码"},
                {"name": "recipient_account", "label": "收款账户"},
            ],
            "field_matches": [{
                "left_field": "payer_id_number", "right_field": "account_owner_id_number",
                "message": "付款人身份与付款账户登记信息不匹配。",
            }],
            "balance_rules": [{"message": "转账金额超过付款账户可用余额。"}],
            "conditional_steps": [{
                "field": "amount", "operator": "gte", "value": 100000,
                "required_step": "authorize_large_transfer", "message": "大额转账缺少主管授权。",
                "before_step": "process_transfer", "order_message": "大额转账授权必须在转账执行前完成。",
            }],
            "available_steps": ["authorize_large_transfer"],
        },
    },
    {
        "id": 5,
        "title": "银行卡挂失",
        "business_type": "loss_reporting",
        "difficulty": "basic",
        "description": "客户申请银行卡挂失，需核验持卡人身份并冻结卡片。",
        "customer_profile": {
            "name": "孙悦", "persona": "刚发现银行卡遗失，比较紧张，担心资金风险。",
            "opening_line": "我的银行卡找不到了，麻烦帮我尽快挂失。",
            "disclosed_facts": {"银行卡号": "C001", "证件号码": "ID001"},
            "internal_notes": ["希望柜员说明冻结后的影响", "不能替柜员完成持卡关系核验"],
        },
        "expected_steps": [
            "greet_customer", "verify_identity", "verify_card_ownership",
            "report_card_loss", "freeze_card", "confirm_receipt",
        ],
        "risk_rules": {},
        "scoring_policy": {"rule_weight": 0.8, "ai_weight": 0.2},
        "rule_policy": {
            "version": 1,
            "enforce_step_order": True,
            "inputs": [
                {"name": "card_number", "label": "银行卡号"},
                {"name": "presented_id_number", "label": "出示证件号码"},
                {"name": "card_owner_id_number", "label": "持卡人登记证件号码"},
            ],
            "field_matches": [{
                "left_field": "presented_id_number", "right_field": "card_owner_id_number",
                "message": "申请人身份与持卡人登记身份不匹配。",
            }],
        },
    },
    {
        "id": 6,
        "title": "银行卡补卡",
        "business_type": "card_replacement",
        "difficulty": "intermediate",
        "description": "已挂失客户申请补卡，需验证挂失记录、身份并完成新卡激活。",
        "customer_profile": {
            "name": "周敏", "persona": "已经电话挂失，来网点补卡，关注费用和旧卡状态。",
            "opening_line": "你好，我之前已经挂失了银行卡，今天来补一张新卡。",
            "disclosed_facts": {"挂失记录编号": "L001", "证件号码": "ID001"},
            "internal_notes": ["询问补卡手续费", "新卡激活前不会假定业务完成"],
        },
        "expected_steps": [
            "greet_customer", "verify_identity", "verify_loss_report", "collect_replacement_fee",
            "replace_card", "activate_card", "confirm_receipt",
        ],
        "risk_rules": {},
        "scoring_policy": {"rule_weight": 0.8, "ai_weight": 0.2},
        "rule_policy": {
            "version": 1,
            "enforce_step_order": True,
            "inputs": [
                {"name": "loss_report_number", "label": "挂失记录编号"},
                {"name": "presented_id_number", "label": "出示证件号码"},
                {"name": "card_owner_id_number", "label": "持卡人登记证件号码"},
                {"name": "replacement_fee", "label": "补卡手续费", "input_type": "number", "minimum": 0},
            ],
            "field_matches": [{
                "left_field": "presented_id_number", "right_field": "card_owner_id_number",
                "message": "补卡申请人身份与持卡人登记身份不匹配。",
            }],
        },
    },
]
