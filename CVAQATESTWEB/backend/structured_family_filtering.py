from typing import Dict, List


class StructuredFamilyFiltering:
    """
    Pure helper to filter cases by multiple criteria.
    This is neutral filtering, not opinionated recommendation.
    """

    @staticmethod
    def apply(
        cases: List[Dict],
        modules: List[str] = None,
        families: List[str] = None,
        execution_modes: List[str] = None,
        automation_levels: List[str] = None,
        priorities: List[str] = None,
    ) -> List[Dict]:
        out = cases[:]

        if modules:
            wanted = set(modules)
            out = [c for c in out if (c.get("category", "") or "") in wanted]

        if families:
            wanted = set(families)
            out = [
                c for c in out
                if ((c.get("family", "") or ((c.get("excel", {}) or {}).get("family", "")) or "generic") in wanted)
            ]

        if execution_modes:
            wanted = {x.lower() for x in execution_modes}
            out = [c for c in out if (c.get("execution_mode", "") or "").lower() in wanted]

        if automation_levels:
            wanted = {x.lower() for x in automation_levels}
            out = [c for c in out if (c.get("automation_level", "") or "").lower() in wanted]

        if priorities:
            wanted = {x.lower() for x in priorities}
            out = [c for c in out if (c.get("priority", "") or "").lower() in wanted]

        return out
