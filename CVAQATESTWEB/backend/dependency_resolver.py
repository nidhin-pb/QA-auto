import re
from typing import Dict, List


class DependencyResolver:
    TICKET_PLACEHOLDER_PATTERNS = [
        r"INC\(ticket number\)",
        r"INC\*+",
        r"INC\(.*?\)",
        r"RITM\(ticket number\)",
        r"RITM\*+",
        r"RITM\(.*?\)",
    ]

    @classmethod
    def replace_ticket_placeholders(cls, text: str, available_tickets: List[str]) -> str:
        if not text or not available_tickets:
            return text

        preferred_inc = next((t for t in reversed(available_tickets) if t.upper().startswith("INC")), None)
        preferred_ritm = next((t for t in reversed(available_tickets) if t.upper().startswith("RITM")), None)

        out = text
        for pat in cls.TICKET_PLACEHOLDER_PATTERNS:
            if re.search(pat, out, flags=re.IGNORECASE):
                replacement = preferred_inc or preferred_ritm or available_tickets[-1]
                out = re.sub(pat, replacement, out, flags=re.IGNORECASE)

        return out

    @classmethod
    def needs_ticket_but_missing(cls, scenario: dict, available_tickets: List[str]) -> bool:
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        requires_ticket = scenario.get("requires_ticket", False)
        initial_message = scenario.get("initial_message", "") or ""
        has_real_ticket = bool(re.search(r"\b(?:INC|RITM)\d{7,10}\b", initial_message, flags=re.IGNORECASE))

        # Queries like "show my open tickets" should never be blocked
        if family == "ticket_query":
            initial_low = initial_message.lower()
            if "open tickets" in initial_low or "show my tickets" in initial_low:
                return False

        if family in ("ticket_create", "service_catalog", "sla_query"):
            return False

        return requires_ticket and (not has_real_ticket) and (not available_tickets)

    @classmethod
    def apply_runtime_context(cls, scenario: dict, available_tickets: List[str]) -> dict:
        updated = dict(scenario)
        updated["initial_message"] = cls.replace_ticket_placeholders(
            updated.get("initial_message", ""),
            available_tickets
        )

        excel = dict(updated.get("excel", {}) or {})
        excel["user_query"] = cls.replace_ticket_placeholders(
            excel.get("user_query", updated.get("initial_message", "")),
            available_tickets
        )
        excel["action"] = cls.replace_ticket_placeholders(excel.get("action", ""), available_tickets)
        excel["expected_response"] = cls.replace_ticket_placeholders(excel.get("expected_response", ""), available_tickets)
        updated["excel"] = excel

        return updated
