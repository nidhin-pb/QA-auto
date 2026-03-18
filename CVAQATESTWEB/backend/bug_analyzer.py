from typing import List


class BugAnalyzer:
    """
    Minimal bug classifier for clearer notes.
    Safe additive helper for now.
    """

    @staticmethod
    def classify(failures: List[str], error_message: str = "") -> str:
        text = " ".join(failures or []) + " " + (error_message or "")
        t = text.lower()

        if "timeout" in t or "no response" in t:
            return "No Response / Timeout"
        if "injection" in t or "unsafe" in t:
            return "Security / Injection Handling"
        if "language mismatch" in t:
            return "Language Handling"
        if "ticket" in t:
            return "Ticket Workflow"
        if "attachment" in t or "file" in t:
            return "Attachment Handling"
        if "handover" in t or "agent" in t:
            return "Agent Handover"
        if "kb" in t or "citation" in t or "troubleshooting" in t:
            return "Knowledge / Troubleshooting"
        if "out-of-scope" in t or "decline" in t:
            return "Intent Routing / Scope"
        return "General Functional"
