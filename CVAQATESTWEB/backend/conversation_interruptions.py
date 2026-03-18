class ConversationInterruptions:
    @staticmethod
    def is_session_expiry_notice(text: str) -> bool:
        low = (text or "").lower()
        return (
            "session expiry notice" in low
            or "your current conversation session will expire" in low
            or "say hi or hello to start a new conversation" in low
            or "start a new conversation" in low
        )

    @staticmethod
    def is_restart_banner(text: str) -> bool:
        low = (text or "").lower()
        return (
            "please start a new conversation" in low
            or "say hi or hello" in low
            or "your session has expired" in low
        )

    @staticmethod
    def is_interruption(text: str) -> bool:
        return (
            ConversationInterruptions.is_session_expiry_notice(text)
            or ConversationInterruptions.is_restart_banner(text)
        )
