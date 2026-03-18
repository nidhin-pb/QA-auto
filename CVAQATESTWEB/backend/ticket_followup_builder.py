from typing import Dict


class TicketFollowUpBuilder:
    @staticmethod
    def build(scenario: Dict, cva_response: str, ticket_id: str = "") -> str:
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        cva = (cva_response or "").lower()

        if family == "ticket_update":
            if "ticket number" in cva or "which ticket" in cva:
                tid = ticket_id or "the latest open incident"
                return (
                    f"The incident number is {tid}. "
                    f"Please add that issue has worsened and is now affecting my ability to work normally."
                )

            if any(x in cva for x in [
                "specific details", "what would you like to add", "what would you like to update",
                "new details", "updates you'd like to add", "updates you'd like to add"
            ]):
                return (
                    f"The incident number is {ticket_id}. "
                    f"New symptoms include issue occurring more frequently. "
                    f"I already tried restarting and problem still persists."
                ) if ticket_id else (
                    "Please update my latest incident. "
                    "New symptoms include issue occurring more frequently, and restarting did not help."
                )

            if ticket_id:
                return (
                    f"The incident number is {ticket_id}. "
                    f"Please update it with these details: issue is still happening, "
                    f"it has become more frequent, and restarting did not resolve it."
                )

            return (
                "Please update my latest incident ticket. "
                "The issue is still happening and has become more frequent. Restarting did not help."
            )

        if family == "ticket_close":
            if "ticket number" in cva or "which ticket" in cva:
                return f"The incident number is {ticket_id}. The issue is fully resolved now. Please close it." if ticket_id else \
                       "Please use my latest incident. The issue is fully resolved now. Please close it."
            if any(x in cva for x in ["confirm", "fully resolved", "resolution summary"]):
                return "Yes, issue is fully resolved now and no further action is needed."
            return "Yes, issue is fully resolved now. Please close the ticket."

        if family == "ticket_query":
            if "ticket number" in cva or "which ticket" in cva:
                return f"Please show me the latest status of {ticket_id}." if ticket_id else "Please show me the latest open incident."
            return ""

        if family == "attachment":
            # IMPORTANT: never invent ticket ids, always use real context ticket
            tid = ticket_id or scenario.get("context_ticket_id", "")

            if "ticket number" in cva or "which ticket" in cva:
                return f"The incident number is {tid}." if tid else "Please use my latest open incident."

            if any(x in cva for x in [
                "upload", "drag and drop", "attach file", "add any files", "use the attachment icon"
            ]):
                # This line should only be used AFTER actual upload succeeded
                return f"I have uploaded file for ticket {tid}. Please attach it and confirm." if tid else \
                       "I have uploaded file. Please attach it to my latest ticket and confirm."

            if any(x in cva for x in ["confirm file name", "file name", "which file"]):
                # Real filename should be injected later by engine if available
                return "The uploaded file is screenshot/log file I just shared."

            if any(x in cva for x in ["unsupported file type", "file size limit", "too large"]):
                return "Understood. Please tell me the supported file types or a recommended alternative."

            return f"Please attach my uploaded file to ticket {tid} and confirm." if tid else \
                   "Please attach my uploaded file to my latest ticket and confirm."

        return ""
