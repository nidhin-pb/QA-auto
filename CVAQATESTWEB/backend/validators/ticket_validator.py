from validators.base_validator import BaseValidator


class TicketValidator(BaseValidator):

    def validate(self, result, conversation):

        action = (result.scenario.get("excel", {}) or {}).get("action", "").lower()
        bot_reply = (result.actual_first_reply or "").lower()
        state = getattr(result, "state", {})

        failures = []

        # ---- CREATE TICKET FLOW ----
        if "create" in action:

            # Case 1: Asking for required details (valid first step)
            if any(x in bot_reply for x in ["provide", "subject", "description", "impact", "urgency", "more details"]):
                return {"passed": True, "failures": [], "notes": ["Asked for required ticket details"]}

            # Case 2: Ticket actually created
            if state.get("ticket_created"):
                return {"passed": True, "failures": [], "notes": ["Ticket created successfully"]}

            failures.append("Ticket creation flow not handled correctly")

        # ---- UPDATE FLOW ----
        if "update" in action:

            # Case 1: Asking for ticket number
            if "ticket number" in bot_reply:
                return {"passed": True, "failures": [], "notes": ["Requested ticket number"]}

            # Case 2: Ticket updated
            if state.get("ticket_updated"):
                return {"passed": True, "failures": [], "notes": ["Ticket updated successfully"]}

            failures.append("Ticket update flow not handled correctly")

        # ---- STATUS FLOW ----
        if "status" in action:
            if "status" in bot_reply or "incident" in bot_reply:
                return {"passed": True, "failures": [], "notes": ["Ticket status handled"]}

        # ---- CLOSE FLOW ----
        if "close" in action:
            if state.get("ticket_closed"):
                return {"passed": True, "failures": [], "notes": ["Ticket closed"]}

        if failures:
            return {"passed": False, "failures": failures, "notes": []}

        return {"passed": True, "failures": [], "notes": ["Ticket validation default pass"]}
