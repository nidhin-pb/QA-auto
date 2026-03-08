from validators.base_validator import BaseValidator


class GreetingValidator(BaseValidator):
    def validate(self, result, conversation):

        bot_reply = (result.actual_first_reply or "").lower()
        expected = (result.scenario.get("excel", {}) or {}).get("expected_response", "").lower()

        # If expected text exists, check semantic alignment
        if expected:
            if any(word in bot_reply for word in ["assist", "help", "support"]):
                return {"passed": True, "failures": [], "notes": ["Greeting aligned semantically"]}

        # Fallback: check for greeting patterns
        if any(x in bot_reply for x in ["hello", "good morning", "welcome"]):
            return {"passed": True, "failures": [], "notes": ["Greeting detected"]}

        return {"passed": False, "failures": ["Greeting response invalid"], "notes": []}
