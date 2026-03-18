from validators.base_validator import BaseValidator
from intent import Intent
from utils import extract_ticket_number, contains_ticket_confirmation, contains_update_confirmation, contains_close_confirmation, contains_ticket_list


class TicketValidator(BaseValidator):

    def validate(self, result, conversation):
        lifecycle = getattr(result, "lifecycle", {}) or {}
        if not isinstance(lifecycle, dict):
            lifecycle = {}

        intent = lifecycle.get("intent")
        stage = lifecycle.get("stage")
        bot_reply = (result.actual_first_reply or "").lower()
        all_bot = "\n\n".join(
            [(m.get("content") or "") for m in (result.conversation_log or []) if (m.get("role") or "").lower() in ("assistant", "cva")]
        )
        text = all_bot or bot_reply
        ticket = extract_ticket_number(text)

        # CREATE
        if intent == Intent.CREATE_TICKET:
            if ticket and (stage == "created" or contains_ticket_confirmation(text)):
                return {"passed": True, "failures": [], "notes": [f"Ticket created/referenced: {ticket}"]}

            if any(x in bot_reply for x in ["subject", "description", "impact", "urgency", "provide", "before i proceed", "employee id"]):
                return {"passed": True, "failures": [], "notes": ["Requested ticket details"]}

            if any(x in bot_reply for x in ["existing ticket", "already have an open incident", "would you like to update"]):
                return {"passed": True, "failures": [], "notes": ["Acceptable alternate: existing ticket offered for update"]}

            return {"passed": False, "failures": ["Ticket creation flow incomplete"], "notes": []}

        # UPDATE
        if intent == Intent.UPDATE_TICKET:
            if stage == "updated" or contains_update_confirmation(text):
                return {"passed": True, "failures": [], "notes": ["Ticket updated"]}

            if "ticket number" in bot_reply or "which ticket" in bot_reply:
                return {"passed": True, "failures": [], "notes": ["Requested ticket number"]}

            return {"passed": False, "failures": ["Ticket update flow incomplete"], "notes": []}

        # STATUS / QUERY
        if intent == Intent.STATUS_CHECK:
            if contains_ticket_list(text) or ticket:
                return {"passed": True, "failures": [], "notes": ["Ticket details/status shown"]}

            if "ticket number" in bot_reply:
                return {"passed": True, "failures": [], "notes": ["Requested ticket identifier"]}

            return {"passed": False, "failures": ["Ticket status/query flow incomplete"], "notes": []}

        # CLOSE
        if intent == Intent.CLOSE_TICKET:
            if stage == "closed" or contains_close_confirmation(text):
                return {"passed": True, "failures": [], "notes": ["Ticket closed"]}

            if any(x in bot_reply for x in ["ticket number", "fully resolved", "resolution summary", "confirm issue"]):
                return {"passed": True, "failures": [], "notes": ["Requested closure confirmation/details"]}

            return {"passed": False, "failures": ["Ticket closure flow incomplete"], "notes": []}

        return {"passed": True, "failures": [], "notes": ["Ticket validation passed"]}
