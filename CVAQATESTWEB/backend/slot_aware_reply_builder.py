from typing import Dict, List


class SlotAwareReplyBuilder:
    """
    Builds a more human and CVA-response-aware follow-up.
    Focus: ticket creation/update style slot filling.
    """

    @staticmethod
    def build(scenario: Dict, cva_response: str, history: List[Dict]) -> str:
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()
        cva = (cva_response or "").lower()

        # Ticket creation / update style slot filling
        if family in ("ticket_create", "ticket_update"):
            problem = SlotAwareReplyBuilder._infer_problem_from_user_history(history)

            parts = []

            if any(x in cva for x in [
                "what specific problems", "what specific problem", "describe the issue",
                "what seems to be the problem", "what issue are you facing"
            ]):
                parts.append(f"The main problem is that {problem}.")

            if any(x in cva for x in [
                "when did the issue start", "when did it start", "when it started"
            ]):
                parts.append("It started today morning.")

            if any(x in cva for x in [
                "what troubleshooting", "have you tried", "steps already", "already tried"
            ]):
                parts.append("I already tried restarting the laptop, but the issue is still happening.")

            if any(x in cva for x in [
                "error code", "error message", "codes displayed", "messages displayed"
            ]):
                parts.append("I am not seeing any specific error code or message.")

            if any(x in cva for x in [
                "would you like to add any files", "attach any files", "screenshots or error logs"
            ]):
                parts.append("I do not have any files to attach right now. Please go ahead.")

            if any(x in cva for x in [
                "employee id", "user id"
            ]):
                parts.append("My employee ID is 123456.")

            if parts:
                return " ".join(parts)

            return f"The issue is that {problem}. It started today morning, I already tried restarting, and there is no specific error code."

        # Ticket close
        if family == "ticket_close":
            parts = []
            if "ticket number" in cva:
                parts.append("The incident number is the one I mentioned earlier.")
            if any(x in cva for x in ["fully resolved", "resolution summary", "confirm"]):
                parts.append("Yes, the issue is fully resolved now and no further action is needed.")
            return " ".join(parts) if parts else "Yes, the issue is fully resolved now. Please close the ticket."

        # Ticket query
        if family == "ticket_query":
            if "specific ticket number" in cva or "which ticket" in cva:
                return "Please show me the details for the latest open incident ticket."
            return ""

        # Handover
        if family == "handover":
            if any(x in cva for x in ["describe the issue", "share more details", "what seems to be the problem"]):
                return "I already tried the recommended troubleshooting and the issue is still not resolved."
            return "I still need help from a human agent."

        # Attachment
        if family == "attachment":
            if any(x in cva for x in ["upload", "drag and drop", "attach"]):
                return "I have uploaded the file. Please confirm whether it was received correctly."
            return "Please continue with the attachment process."

        # Default
        return ""

    @staticmethod
    def _infer_problem_from_user_history(history: List[Dict]) -> str:
        user_msgs = [m.get("content", "") for m in history if m.get("role") == "user"]
        joined = " ".join(user_msgs).lower()

        if "slow" in joined:
            return "the laptop is running very slow and occasionally freezing"
        if "black screen" in joined or "screen black" in joined:
            return "the laptop screen stays black and does not display anything properly"
        if "vpn" in joined:
            return "the VPN connection keeps dropping and I cannot work properly"
        if "printer" in joined:
            return "the printer is not working and I cannot print my documents"
        return "the laptop is not working properly"
