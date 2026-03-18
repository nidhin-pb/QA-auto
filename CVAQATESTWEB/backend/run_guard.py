from typing import Dict


class RunGuard:
    """
    Prevent clearly non-runnable structured scenarios from being executed
    through Teams chat runner.
    """

    @staticmethod
    def should_skip(scenario: Dict) -> str:
        automation = (scenario.get("automation_level") or "").lower()
        mode = (scenario.get("execution_mode") or "").lower()
        title = ((scenario.get("excel", {}) or {}).get("scenario_title", "") or scenario.get("name", "")).lower()

        if automation == "manual":
            return "Skipped: scenario classified as manual-only"

        if mode == "performance":
            return "Skipped: performance/load scenario requires separate framework"

        if any(x in title for x in [
            "screen reader", "nvda", "jaws",
            "browser dev tools", "tls", "data residency", "audit trail",
            "95th percentile", "500 concurrent users", "50 concurrent users"
        ]):
            return "Skipped: scenario requires external/manual verification"

        return ""
