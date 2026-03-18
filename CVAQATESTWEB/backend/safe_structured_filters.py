from typing import List, Dict
from scenario_family_mapper import ScenarioFamilyMapper


SUPPORTED_FIRST_RUN_FAMILIES = {
    "knowledge_lookup",
    "knowledge_fallback",
    "ticket_create",
    "ticket_update",
    "ticket_close",
    "ticket_query",
    "service_catalog",
    "attachment",
    "handover",
    "injection",
    "conversation_flow",
    "language",
    "sensitive_hr",
    "security_policy",
    "sla_query",
    "change_calendar",
    "approval_workflow",
}

EXCLUDED_FIRST_RUN_FAMILIES = {
    "generic",
}


def get_safe_structured_subset(cases: List[Dict]) -> List[Dict]:
    safe_modes = {"chat_single_turn", "chat_multi_turn", "ticket_operation", "attachment", "handover", "injection", "session"}

    out = []
    for c in cases:
        level = (c.get("automation_level", "") or "").lower()
        mode = (c.get("execution_mode", "") or "").lower()

        if level != "full":
            continue
        if mode not in safe_modes:
            continue

        family = ScenarioFamilyMapper.get_family(c)

        if family in EXCLUDED_FIRST_RUN_FAMILIES:
            continue
        if family not in SUPPORTED_FIRST_RUN_FAMILIES:
            continue

        out.append(c)

    return out


def get_recommended_first_run_subset(cases: List[Dict]) -> List[Dict]:
    safe = get_safe_structured_subset(cases)

    preferred_order = {
        "knowledge_lookup": 0,
        "ticket_create": 1,
        "ticket_query": 2,
        "ticket_update": 3,
        "ticket_close": 4,
        "service_catalog": 5,
        "sla_query": 6,
        "change_calendar": 7,
        "approval_workflow": 8,
        "attachment": 9,
        "handover": 10,
        "injection": 11,
        "conversation_flow": 12,
        "knowledge_fallback": 13,
        "language": 14,
        "security_policy": 15,
        "sensitive_hr": 16,
    }

    def score(c: Dict):
        family = ScenarioFamilyMapper.get_family(c)
        priority = (c.get("priority", "") or "").lower()
        pscore = {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(priority, 2)
        fscore = preferred_order.get(family, 99)
        return (fscore, pscore, c.get("id", ""))

    return sorted(safe, key=score)
