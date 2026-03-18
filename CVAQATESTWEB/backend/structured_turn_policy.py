from typing import Dict


class StructuredTurnPolicy:
    @staticmethod
    def max_turns_for(scenario: Dict) -> int:
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        mode = (scenario.get("execution_mode", "") or "").lower()

        if family in ("ticket_query", "knowledge_fallback", "service_catalog"):
            return 1

        if family == "knowledge_lookup":
            return 2  # Allow one follow-up for progressive refinement

        if family == "ticket_create":
            return 3

        if family in ("ticket_update", "ticket_close"):
            return 3

        if family == "attachment":
            return 3

        if family == "handover":
            return 3

        if family == "injection":
            return 1

        if family in ("security_policy", "sensitive_hr"):
            return 1

        if family == "sla_query":
            return 2

        if family in ("change_calendar", "approval_workflow"):
            return 2

        if family == "language":
            return 2

        if family == "conversation_flow":
            return 3

        if mode == "chat_single_turn":
            return 1

        if mode == "session":
            return 2

        return int(scenario.get("max_turns", 4) or 4)

    @staticmethod
    def should_stop_after_first_response(scenario: Dict) -> bool:
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        mode = (scenario.get("execution_mode", "") or "").lower()

        if family in (
            "ticket_query", "knowledge_fallback", "service_catalog",
            "injection", "security_policy", "sensitive_hr",
        ):
            return True

        if mode == "chat_single_turn":
            return True

        return False
