from typing import Dict, List
from slot_aware_reply_builder import SlotAwareReplyBuilder


class StructuredFollowUpV2:
    @staticmethod
    def next_user_reply(scenario: Dict, history: List[Dict], cva_response: str) -> str:
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        cva = (cva_response or "").lower()

        slot_reply = SlotAwareReplyBuilder.build(scenario, cva_response, history)
        if slot_reply:
            return slot_reply

        if family == "ticket_create":
            return (
                "The main problem is that the laptop is running very slowly and freezing. "
                "It started today morning, I already tried restarting, and I do not see any error code."
            )

        if family == "ticket_update":
            ticket_id = scenario.get("context_ticket_id", "")
            if ticket_id:
                return (
                    f"The incident number is {ticket_id}. "
                    f"The issue is still happening and has become more severe. "
                    f"I already tried restarting and it did not help."
                )
            return (
                "Please update my latest incident ticket. "
                "The issue is still happening and has become more severe. Restarting did not help."
            )

        if family == "ticket_close":
            return "Yes, the issue is fully resolved now. Please close the ticket."

        if family == "service_catalog":
            if "complete this request" in cva or "select the appropriate form" in cva:
                return 'I need standard software on my desktop, so I will use the "Install Software" request.'
            return ""

        if family == "sla_query":
            ticket_id = scenario.get("context_ticket_id", "")
            if "ticket number" in cva or "which ticket" in cva:
                return f"The incident number is {ticket_id}." if ticket_id else "Please use my latest incident."
            return ""

        if family == "change_calendar":
            if "which system" in cva or "what system" in cva:
                return "The system is CRM."
            return "I want to know if there are any upcoming approved changes for the CRM system."

        if family == "approval_workflow":
            if "which approval" in cva or "pending approvals" in cva:
                return "Please check any pending approvals related to my recent requests."
            return "Can you check my pending approvals in ServiceNow?"

        if family == "attachment":
            ticket_id = scenario.get("context_ticket_id", "")

            if any(x in cva for x in ["ticket number", "which incident", "which ticket"]):
                return f"The incident number is {ticket_id}." if ticket_id else "Please use my latest incident."

            if any(x in cva for x in ["upload", "drag and drop", "attachment icon", "attach file", "upload your file"]):
                return f"I have uploaded the file for ticket {ticket_id}. Please attach it and confirm." if ticket_id else \
                       "I have uploaded the file. Please attach it to my latest ticket and confirm."

            if any(x in cva for x in ["file name", "which file"]):
                files = scenario.get("uploaded_file_names", [])
                if files:
                    return f"The file name is {files[0]}. Please attach it to ticket {ticket_id}."
                return f"Please attach the uploaded file to ticket {ticket_id}." if ticket_id else "Please attach the uploaded file to my latest ticket."

            return ""

        if family == "handover":
            if any(x in cva for x in ["describe the issue", "share more details", "what seems to be the problem"]):
                return "I already tried the recommended steps and the issue still is not resolved."
            return "I still need help from a human agent."

        if family == "conversation_flow":
            if any(x in cva for x in ["clarify", "please provide more details", "which one do you mean"]):
                return "I mean the first option you suggested."
            return "I tried that and the issue is still happening. What should I do next?"

        return ""
