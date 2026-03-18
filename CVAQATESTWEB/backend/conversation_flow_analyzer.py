from typing import Dict, List


class ConversationFlowAnalyzer:
    """
    Analyze whether bot stayed on topic, asked clarifying questions,
    drifted, and whether it recovered after drift.
    """

    @staticmethod
    def analyze(result) -> Dict:
        messages = result.conversation_log or []
        user_msgs = [m.get("content", "") for m in messages if (m.get("role") or "").lower() == "user"]
        bot_msgs = [m.get("content", "") for m in messages if (m.get("role") or "").lower() in ("assistant", "cva")]

        all_user = " ".join(user_msgs).lower()
        all_bot = "\n\n".join(bot_msgs)
        low_bot = all_bot.lower()

        topic = ConversationFlowAnalyzer._infer_primary_topic(all_user)

        asks_questions = any("?" in (m or "") for m in bot_msgs)
        asks_clarification = any(x in low_bot for x in [
            "please provide", "could you clarify", "what do you mean", "which one",
            "can you confirm", "let me know", "share more details"
        ])

        drift_detected, drift_reason = ConversationFlowAnalyzer._detect_drift(topic, low_bot)
        user_corrected_bot = any(
            any(x in (msg.get("content") or "").lower() for x in [
                "there's been a misunderstanding",
                "my issue is not",
                "that's not the issue",
                "i meant",
                "not outlook",
                "not email",
                "not vpn"
            ])
            for msg in messages if (msg.get("role") or "").lower() == "user"
        )

        recovery_after_drift = False
        if drift_detected and user_corrected_bot:
            recovery_after_drift = ConversationFlowAnalyzer._bot_recovered_after_correction(messages, topic)

        return {
            "topic": topic,
            "asks_questions": asks_questions,
            "asks_clarification": asks_clarification,
            "drift_detected": drift_detected,
            "drift_reason": drift_reason,
            "user_corrected_bot": user_corrected_bot,
            "recovery_after_drift": recovery_after_drift,
        }

    @staticmethod
    def _infer_primary_topic(user_text: str) -> str:
        t = (user_text or "").lower()

        if any(x in t for x in ["email", "outlook", "mailbox", "syncing", "outbox", "cannot send"]):
            return "email"
        if any(x in t for x in ["vpn", "wifi", "network", "internet", "server failed", "connection", "wireless adapter"]):
            return "network"
        if any(x in t for x in ["laptop", "computer", "slow", "freezing", "screen", "battery"]):
            return "laptop"
        if any(x in t for x in ["ticket", "incident", "servicenow"]):
            return "ticket"
        return "generic"

    @staticmethod
    def _detect_drift(topic: str, bot_text: str):
        low = (bot_text or "").lower()

        if topic == "email":
            if any(x in low for x in ["windows hello", "tpm", "hello for business", "azure ad-joined", "dsregcmd"]):
                return True, "Bot drifted from email issue into Windows Hello / identity troubleshooting"

        if topic == "network":
            if any(x in low for x in ["outlook email", "mailbox full", "cannot send emails"]) and not any(x in low for x in ["wifi", "wireless", "network adapter", "internet connection"]):
                return True, "Bot drifted from network issue into email troubleshooting"

        if topic == "laptop":
            if any(x in low for x in ["windows hello", "hello for business"]) and not any(x in low for x in ["screen", "memory", "performance", "battery", "task manager"]):
                return True, "Bot drifted from laptop issue into identity troubleshooting"

        return False, ""

    @staticmethod
    def _bot_recovered_after_correction(messages: List[Dict], topic: str) -> bool:
        bot_msgs = [m.get("content", "") for m in messages if (m.get("role") or "").lower() in ("assistant", "cva")]
        low_bot = " ".join(bot_msgs).lower()

        if topic == "network":
            return any(x in low_bot for x in ["wireless adapter", "wifi", "available networks", "forget network"])
        if topic == "email":
            return any(x in low_bot for x in ["outbox", "receive emails", "send emails", "outlook"])
        if topic == "laptop":
            return any(x in low_bot for x in ["screen", "memory", "task manager", "battery", "performance"])

        return False
