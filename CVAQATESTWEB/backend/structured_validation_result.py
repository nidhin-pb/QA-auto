from typing import List, Dict, Any


class StructuredValidationResult:
    @staticmethod
    def make(
        passed: bool,
        notes: List[str] = None,
        failures: List[str] = None,
        alternate: bool = False,
        alternate_reason: str = "",
    ) -> Dict[str, Any]:
        return {
            "passed": bool(passed),
            "failures": failures or [],
            "notes": notes or [],
            "alternate": alternate,
            "alternate_reason": alternate_reason or "",
        }
