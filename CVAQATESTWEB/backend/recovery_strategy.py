from typing import Dict, List
from conversation_interruptions import ConversationInterruptions


class RecoveryStrategy:
    @staticmethod
    def recover_message_for_interruption(scenario: Dict, history: List[Dict]) -> str:
        """
        If session expiry or restart banner occurs, send a short natural restart
        and then re-issue the original intent.
        """
        original = (scenario.get("initial_message") or "").strip()
        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()

        if family == "ticket_query":
            return "Hi, can you show me my open tickets?"

        if family == "knowledge_lookup":
            return original or "Hi, my laptop is running very slow. Can you help me troubleshoot it?"

        if family == "ticket_create":
            return original or "Hi, I need help raising an incident for my laptop issue."

        return f"Hi, {original}" if original else "Hi, I need help."
