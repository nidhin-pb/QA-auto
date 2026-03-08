class BaseValidator:
    def validate(self, result, conversation):
        """
        Return dict:
        {
            "passed": bool,
            "failures": list[str],
            "notes": list[str]
        }
        """
        return {
            "passed": True,
            "failures": [],
            "notes": ["Base validator used (no specific rules applied)"]
        }
