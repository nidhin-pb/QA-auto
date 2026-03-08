from validators.base_validator import BaseValidator


class CatalogValidator(BaseValidator):
    def validate(self, result, conversation):
        expected = (result.scenario.get("excel", {}) or {}).get("expected_response", "")
        bot_reply = (result.actual_first_reply or "").lower()

        missing_items = []

        for line in expected.split("\n"):
            clean = line.strip()
            if clean and clean.lower() not in bot_reply:
                missing_items.append(clean)

        if missing_items:
            return {
                "passed": False,
                "failures": ["Missing expected catalog items: " + ", ".join(missing_items)],
                "notes": []
            }

        return {
            "passed": True,
            "failures": [],
            "notes": ["Catalog items validated"]
        }
