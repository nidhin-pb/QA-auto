import re
from typing import Dict, List, Optional


class TicketContextManager:
    """
    Chooses best ticket context for structured ticket scenarios.
    """

    @staticmethod
    def extract_real_ticket_from_text(text: str) -> Optional[str]:
        if not text:
            return None
        m = re.search(r"\b(?:INC|RITM)\d{7,10}\b", text, flags=re.IGNORECASE)
        return m.group(0).upper() if m else None

    @staticmethod
    def choose_ticket_for_scenario(scenario: Dict, confirmed_tickets: List[str], discovered_tickets: List[str]) -> Optional[str]:
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        initial = scenario.get("initial_message", "") or ""
        action = ((scenario.get("excel", {}) or {}).get("action", "") or scenario.get("goal", "") or "").lower()

        # If scenario already contains a real ticket number, use it
        explicit = TicketContextManager.extract_real_ticket_from_text(initial)
        if explicit:
            return explicit

        # Prefer confirmed over discovered
        pool = list(reversed(confirmed_tickets or [])) + [t for t in reversed(discovered_tickets or []) if t not in (confirmed_tickets or [])]

        if not pool:
            return None

        # For SLA / query / update / close, prefer latest INC
        if family in ("ticket_query", "ticket_update", "ticket_close"):
            inc = next((t for t in pool if t.startswith("INC")), None)
            if inc:
                return inc

        # Service catalog / request paths may prefer RITM
        if family == "service_catalog":
            ritm = next((t for t in pool if t.startswith("RITM")), None)
            if ritm:
                return ritm

        return pool[0]

    @staticmethod
    def inject_ticket_into_scenario(scenario: Dict, ticket_id: Optional[str]) -> Dict:
        updated = dict(scenario)
        if not ticket_id:
            return updated

        initial = updated.get("initial_message", "") or ""
        excel = dict(updated.get("excel", {}) or {})

        # Replace placeholders if present
        patterns = [
            r"INC\(ticket number\)",
            r"INC\*+",
            r"INC\(.*?\)",
            r"RITM\(ticket number\)",
            r"RITM\*+",
            r"RITM\(.*?\)",
        ]

        for pat in patterns:
            initial = re.sub(pat, ticket_id, initial, flags=re.IGNORECASE)
            excel["user_query"] = re.sub(pat, ticket_id, excel.get("user_query", initial), flags=re.IGNORECASE)
            excel["action"] = re.sub(pat, ticket_id, excel.get("action", ""), flags=re.IGNORECASE)
            excel["expected_response"] = re.sub(pat, ticket_id, excel.get("expected_response", ""), flags=re.IGNORECASE)

        updated["initial_message"] = initial
        updated["excel"] = excel
        updated["context_ticket_id"] = ticket_id

        return updated

    @staticmethod
    def build_ticket_intent_message(scenario: Dict, ticket_id: Optional[str]) -> str:
        """
        If no explicit user query exists, synthesize a good ticket-specific message.
        """
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        if not ticket_id:
            return scenario.get("initial_message", "") or ""

        if family == "ticket_query":
            return f"Can you show me latest status of {ticket_id}?"
        if family == "ticket_update":
            return f"I need to update {ticket_id} with more information."
        if family == "ticket_close":
            return f"Please close {ticket_id}. The issue is resolved."
        return scenario.get("initial_message", "") or ""
