from typing import Dict


def is_structured_scenario(scenario: Dict) -> bool:
    return bool(scenario.get("execution_mode") or scenario.get("automation_level"))


def should_skip_for_manual(scenario: Dict) -> bool:
    return (scenario.get("automation_level") or "").lower() == "manual"


def should_warn_for_partial(scenario: Dict) -> bool:
    return (scenario.get("automation_level") or "").lower() == "partial"
