from typing import Dict, List, Optional


class AttachmentContextManager:
    @staticmethod
    def choose_ticket_for_attachment(confirmed_tickets: List[str], discovered_tickets: List[str]) -> Optional[str]:
        pool = list(reversed(confirmed_tickets or [])) + [t for t in reversed(discovered_tickets or []) if t not in (confirmed_tickets or [])]
        inc = next((t for t in pool if t.startswith("INC")), None)
        if inc:
            return inc
        ritm = next((t for t in pool if t.startswith("RITM")), None)
        return ritm or (pool[0] if pool else None)

    @staticmethod
    def inject_attachment_ticket_context(scenario: Dict, ticket_id: Optional[str]) -> Dict:
        updated = dict(scenario)
        if ticket_id:
            updated["context_ticket_id"] = ticket_id
        return updated

    @staticmethod
    def build_attachment_initial_message(scenario: Dict, ticket_id: Optional[str]) -> str:
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        title = ((scenario.get("excel", {}) or {}).get("scenario_title", "") or scenario.get("name", "")).lower()

        if family != "attachment":
            return scenario.get("initial_message", "") or ""

        if "unsupported file type" in title:
            return f"I want to attach a file to my ticket {ticket_id or ''}. Can you help me?" .strip()

        if "file size" in title:
            return f"I need to upload a large file to ticket {ticket_id or ''}. Can you help me attach it?" .strip()

        if "screenshot" in title:
            return f"I want to attach a screenshot to my ticket {ticket_id or ''} so IT can review the issue." .strip()

        if "log file" in title:
            return f"I want to attach a log file to my ticket {ticket_id or ''}." .strip()

        return f"I want to attach a file to my latest ticket {ticket_id or ''}." .strip()
