from validators.base_validator import BaseValidator


class OutOfScopeValidator(BaseValidator):
    def validate(self, result, conversation):

        bot_reply = (result.actual_first_reply or "").lower()
        expected = (result.scenario.get("excel", {}) or {}).get("expected_response", "").lower()

        # If expected mentions HR or finance, check for that
        if "finance" in expected or "hr" in expected:
            if "hr" in bot_reply or "finance" in bot_reply:
                return {"passed": True, "failures": [], "notes": ["Proper HR/Finance redirection"]}

        # General out-of-scope check
        if "it" in bot_reply and "servicenow" in bot_reply:
            return {"passed": True, "failures": [], "notes": ["Proper IT-only restriction"]}

        return {"passed": False, "failures": ["Out-of-scope decline missing"], "notes": []}
