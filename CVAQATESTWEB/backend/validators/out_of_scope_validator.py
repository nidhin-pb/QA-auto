import re
from validators.base_validator import BaseValidator


class OutOfScopeValidator(BaseValidator):

    def validate(self, result, conversation):
        bot_reply = (result.actual_first_reply or "").lower()

        # Strong decline / redirect patterns
        patterns = [
            r"\bonly assist with\b",
            r"\bit support\b",
            r"\bservicenow\b",
            r"\bnot supported through this platform\b",
            r"\bplease use\b",
            r"\bcontact hr\b",
            r"\bemployee self-service\b",
            r"\bhr self-service\b",
            r"\bprivacy and security reasons\b",
        ]

        if any(re.search(p, bot_reply) for p in patterns):
            return {"passed": True, "failures": [], "notes": ["Proper decline/redirection detected"]}

        # Accept valid service request alternate for leave-related queries
        if ("leave request" in bot_reply or "complete this request" in bot_reply or "request form" in bot_reply):
            return {"passed": True, "failures": [], "notes": ["Acceptable alternate: request form shown"]}

        return {"passed": False, "failures": ["Out-of-scope decline missing"], "notes": []}
