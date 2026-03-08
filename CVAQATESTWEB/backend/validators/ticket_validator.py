from validators.base_validator import BaseValidator
from utils import extract_ticket_number


class TicketValidator(BaseValidator):
    def validate(self, result, conversation):
        action = (result.scenario.get("excel", {}) or {}).get("action", "").lower()
        state = getattr(result, "state", {})
        all_text = " ".join(
            m.get("content", "") for m in conversation if m.get("role") == "assistant"
        ).lower()

        failures = []

        # CREATE
        if "create" in action:
            if not state.get("ticket_created"):
                failures.append("Ticket was not created")

        # UPDATE
        if "update" in action:
            if not state.get("ticket_updated"):
                failures.append("Ticket was not updated")

        # RESOLVE
        if "resolve" in action:
            if not state.get("ticket_resolved"):
                failures.append("Ticket was not resolved")

        # CLOSE
        if "close" in action:
            if not state.get("ticket_closed"):
                failures.append("Ticket was not closed")

        # STATUS CHECK
        if "status" in action:
            if not extract_ticket_number(all_text):
                failures.append("Ticket status not retrieved")

        if failures:
            return {
                "passed": False,
                "failures": failures,
                "notes": []
            }

        return {
            "passed": True,
            "failures": [],
            "notes": ["Ticket lifecycle validated"]
        }
