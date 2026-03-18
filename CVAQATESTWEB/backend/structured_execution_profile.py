from typing import Dict


class StructuredExecutionProfile:
    """
    Defines what execution modes are currently safe to run
    with existing Teams chat automation.
    """

    SAFE_AUTOMATION_LEVELS = {"full"}
    SAFE_EXECUTION_MODES = {
        "chat_single_turn",
        "chat_multi_turn",
        "ticket_operation",
        "attachment",
        "handover",
        "injection",
        "session",
    }

    @classmethod
    def is_supported_now(cls, scenario: Dict) -> bool:
        level = (scenario.get("automation_level", "") or "").lower()
        mode = (scenario.get("execution_mode", "") or "").lower()

        if level not in cls.SAFE_AUTOMATION_LEVELS:
            return False
        if mode not in cls.SAFE_EXECUTION_MODES:
            return False
        return True

    @classmethod
    def reason_unsupported(cls, scenario: Dict) -> str:
        level = (scenario.get("automation_level", "") or "").lower()
        mode = (scenario.get("execution_mode", "") or "").lower()

        if level not in cls.SAFE_AUTOMATION_LEVELS:
            return f"Automation level '{level}' not supported in current runner"
        if mode not in cls.SAFE_EXECUTION_MODES:
            return f"Execution mode '{mode}' not supported in current runner"
        return ""
