from typing import Dict
from utils import (
    extract_all_ticket_numbers,
    extract_ticket_number,
    contains_ticket_confirmation,
    contains_ticket_list,
    contains_update_confirmation,
    contains_close_confirmation,
)


class TicketWorkflowResolver:
    @staticmethod
    def resolve(result) -> Dict:
        all_bot = "\n\n".join(
            [(m.get("content") or "") for m in (result.conversation_log or []) if (m.get("role") or "").lower() in ("assistant", "cva")]
        )
        low = all_bot.lower()
        tickets = extract_all_ticket_numbers(all_bot)
        latest_ticket = tickets[-1] if tickets else None

        outcome = {
            "final_path": "",
            "ticket_id": latest_ticket,
            "notes": [],
            "alternate": False,
            "alternate_reason": "",
        }

        family = ((result.scenario.get("excel", {}) or {}).get("family", "") or result.scenario.get("family", "")).lower()

        if family == "ticket_create":
            if any(x in low for x in [
                "your new incident ticket",
                "new incident ticket",
                "has been created successfully",
                "has been successfully created",
                "incident number:",
                "status: new",
                "a new incident ticket has been created",
                "incident ticket has been successfully created",
                "ticket has been successfully created",
            ]) and contains_ticket_confirmation(all_bot):
                outcome["final_path"] = "new_ticket_created"
                outcome["notes"].append(f"New ticket created: {latest_ticket or 'ticket detected'}")
                return outcome

            if contains_update_confirmation(all_bot) or any(x in low for x in [
                "updated successfully",
                "updated with the latest details",
                "view your updated incident",
                "status: in progress"
            ]):
                outcome["final_path"] = "existing_ticket_updated"
                outcome["alternate"] = True
                outcome["alternate_reason"] = "CVA reused or updated an existing incident instead of creating a duplicate"
                outcome["notes"].append(f"Existing ticket updated: {latest_ticket or 'ticket detected'}")
                return outcome

        if family == "ticket_update":
            if contains_update_confirmation(all_bot) or any(x in low for x in [
                "has been updated",
                "updated with the new details",
                "view inc",
                "view your updated incident",
                "status: in progress"
            ]):
                ticket = extract_ticket_number(all_bot) or latest_ticket
                outcome["final_path"] = "ticket_updated"
                outcome["ticket_id"] = ticket
                outcome["notes"].append(f"Ticket updated: {ticket or 'ticket detected'}")
                return outcome

        if family == "ticket_close":
            if contains_close_confirmation(all_bot):
                ticket = extract_ticket_number(all_bot) or latest_ticket
                outcome["final_path"] = "ticket_closed"
                outcome["ticket_id"] = ticket
                outcome["notes"].append(f"Ticket closed: {ticket or 'ticket detected'}")
                return outcome

        if family == "ticket_query":
            if contains_ticket_list(all_bot):
                first_ticket = tickets[0] if tickets else latest_ticket
                outcome["final_path"] = "ticket_list_retrieved"
                outcome["ticket_id"] = first_ticket
                outcome["notes"].append(f"Ticket list retrieved: {', '.join(tickets[:5])}")
                return outcome

        if family == "attachment":
            if any(x in low for x in [
                "file attached",
                "attached successfully",
                "attachment added",
                "attached to your incident",
                "upload your file",
                "unsupported file type",
                "file size limit",
                "too large"
            ]):
                outcome["final_path"] = "attachment_handled"
                outcome["notes"].append("Attachment flow handled")
                return outcome

        if any(x in low for x in [
            "please provide",
            "what specific problems",
            "when did the issue start",
            "could you clarify",
            "have you tried"
        ]):
            outcome["final_path"] = "slot_filling_only"
            outcome["alternate"] = True
            outcome["alternate_reason"] = "Valid workflow started, but final ticket action did not complete yet"
            outcome["notes"].append("Ticket workflow remained in slot-filling stage")
            return outcome

        return outcome
