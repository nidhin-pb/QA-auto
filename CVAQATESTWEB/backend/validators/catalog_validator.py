import re
from validators.base_validator import BaseValidator


def normalize(text):
    return re.sub(r'[^a-z0-9]', '', text.lower())


class CatalogValidator(BaseValidator):

    def validate(self, result, conversation):

        expected = (result.scenario.get("excel", {}) or {}).get("expected_response", "")
        bot_reply = result.actual_first_reply or ""

        expected_items = {normalize(x) for x in expected.split("\n") if x.strip()}
        returned_items = {normalize(x) for x in bot_reply.split("\n") if x.strip()}

        missing = expected_items - returned_items

        if missing:
            return {"passed": False, "failures": [f"Missing catalog items: {missing}"], "notes": []}

        return {"passed": True, "failures": [], "notes": ["Catalog validated"]}
