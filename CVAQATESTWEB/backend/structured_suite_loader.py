from typing import Dict

from scenario_normalizer import load_structured_workbook
from scenario_interpreter import ScenarioInterpreter
from execution_planner import ExecutionPlanner


def load_and_plan_structured_suite(filename: str, raw: bytes) -> Dict:
    parsed = load_structured_workbook(filename, raw)
    records = parsed.get("records", [])

    interpreter = ScenarioInterpreter()
    interpreted = []
    for r in records:
        try:
            interpreted.append(interpreter.interpret(r))
        except Exception as e:
            parsed.setdefault("errors", []).append(f"Interpretation error for {getattr(r, 'scenario_id', 'unknown')}: {e}")

    planner = ExecutionPlanner()
    plan = planner.plan(interpreted)

    legacy_cases = []
    for r in plan["ordered_records"]:
        try:
            legacy = r.to_legacy_scenario()
            legacy_cases.append(legacy)
        except Exception as e:
            parsed.setdefault("errors", []).append(f"Legacy conversion error for {getattr(r, 'scenario_id', 'unknown')}: {e}")

    preview = []
    for r in plan["ordered_records"][:100]:
        try:
            preview.append({
                "scenario_id": r.scenario_id,
                "title": r.scenario_title,
                "module": r.module,
                "focus_area": r.focus_area,
                "scenario_type": r.scenario_type,
                "priority": r.priority,
                "test_type": r.test_type,
                "automation_level": r.automation_level.value,
                "execution_mode": r.execution_mode.value,
                "requires_ticket": r.requires_ticket,
                "requires_attachment": r.requires_attachment,
                "requires_card_interaction": r.requires_card_interaction,
                "family": r.family,
            })
        except Exception as e:
            parsed.setdefault("errors", []).append(f"Preview build error: {e}")

    return {
        "suite_name": parsed.get("suite_name", filename),
        "errors": parsed.get("errors", []),
        "sheet_summaries": parsed.get("sheet_summaries", []),
        "records": interpreted,
        "legacy_cases": legacy_cases,
        "plan_summary": plan["summary"],
        "preview": preview,
    }
