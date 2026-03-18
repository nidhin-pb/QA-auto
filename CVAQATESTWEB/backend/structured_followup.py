from typing import Dict, List


class StructuredFollowUp:
    """
    Scenario-aware fallback follow-up prompts for structured scenarios.
    These are used only as safe templates; AI can still assist.
    """

    @staticmethod
    def next_user_reply(scenario: Dict, history: List[Dict], cva_response: str) -> str:
        mode = (scenario.get("execution_mode", "") or "").lower()
        title = ((scenario.get("excel", {}) or {}).get("scenario_title", "") or scenario.get("name", "")).lower()
        cva = (cva_response or "").lower()

        # Ticket flows
        if mode == "ticket_operation":
            if "ticket number" in cva or "incident number" in cva:
                return "The incident number is the one from my previous ticket. Please continue."
            if any(x in cva for x in ["could you provide", "please provide", "before i proceed"]):
                if "employee id" in cva:
                    return "My employee ID is 123456."
                if "priority" in cva:
                    return "Please mark it as high priority because it is affecting my work."
                return "The issue started today, I already tried restarting, and it is still happening."
            if "existing ticket" in cva:
                return "Yes, please update the existing ticket with these latest details."
            return "Please continue with the ticket workflow."

        # Handover flows
        if mode == "handover":
            if any(x in cva for x in ["please describe", "what seems to be the issue", "can you share more details"]):
                return "I already tried the recommended steps and the issue is still not resolved."
            if any(x in cva for x in ["queue", "wait", "callback", "outside support hours"]):
                return "If an agent is not available, please create a ticket or suggest the next best option."
            return "I still need help from a human agent if possible."

        # Attachment flows
        if mode == "attachment":
            if any(x in cva for x in ["upload", "drag and drop", "attach"]):
                return "I have uploaded the file. Please confirm whether it was received correctly."
            if any(x in cva for x in ["unsupported", "file type", "size limit"]):
                return "Understood. Please tell me the supported file types or alternatives."
            return "Please continue with the attachment handling."

        # Injection flows
        if mode == "injection":
            return "Why can't you do that? Please explain your limitation clearly."

        # Multi-turn knowledge / context
        if mode == "chat_multi_turn":
            if "french" in title:
                return "Pouvez-vous continuer en français s'il vous plaît ?"
            if any(x in cva for x in ["could you clarify", "please provide more details", "what exactly"]):
                return "The issue affects my work laptop and started this morning after I logged in."
            if "options" in cva or "which one" in cva:
                return "I mean the first option you mentioned."
            return "I tried that, but the problem is still happening. What should I do next?"

        # Default
        return "Can you help me with the next step?"
