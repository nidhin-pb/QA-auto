from typing import Dict
from human_prompt_templates import HumanPromptTemplates
from scenario_family_mapper import ScenarioFamilyMapper


class StructuredPromptOverrides:
    @staticmethod
    def apply(scenario: Dict) -> Dict:
        updated = dict(scenario)

        family = ScenarioFamilyMapper.get_family(updated)
        updated["family"] = family
        updated.setdefault("excel", {})
        updated["excel"]["family"] = family

        current = (updated.get("initial_message") or "").strip()
        excel = updated.get("excel", {}) or {}
        user_query_from_excel = (excel.get("user_query") or "").strip()
        test_objective = (excel.get("test_objective") or "").strip()

        bad_starts = [
            "verify ", "validate ", "ensure ", "confirm ",
            "check whether ", "test that ", "assert ",
        ]

        def _is_bad_prompt(text: str) -> bool:
            if not text:
                return True
            low = text.lower().strip()
            if any(low.startswith(x) for x in bad_starts):
                return True
            if low == "i need help with an it issue.":
                return True
            if len(low) < 8:
                return True
            return False

        # Priority 1: If Excel has a good user_query, always use it
        if user_query_from_excel and not _is_bad_prompt(user_query_from_excel):
            updated["initial_message"] = user_query_from_excel
            updated["excel"]["user_query"] = user_query_from_excel
            return updated

        # Priority 2: If current initial_message is already good, keep it
        if current and not _is_bad_prompt(current):
            return updated

        # Priority 3: Use family-specific template (covers most cases well)
        prompt = HumanPromptTemplates.build(updated)
        if prompt and len(prompt.strip()) > 10:
            updated["initial_message"] = prompt
            updated["excel"]["user_query"] = prompt
            return updated

        # Priority 4: If nothing else, AI will generate in test_engine
        # (generate_structured_initial_message handles this)
        return updated
