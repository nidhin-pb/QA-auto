"""
Test Engine v5 - Fixed goal achievement to require multi-step goals.
"""
import asyncio
import traceback
from typing import List, Dict, Optional
from datetime import datetime

from config import app_config
from ai_brain import AIBrain
from teams_automator import TeamsAutomator
from test_scenarios import get_all_scenarios
from report_generator import ReportGenerator
from websocket_manager import ws_manager
from utils import (
    timestamp_readable, contains_ticket_confirmation, contains_ticket_list,
    contains_citation, contains_follow_up_question, contains_update_confirmation,
    contains_resolve_confirmation, contains_close_confirmation,
    contains_live_agent_handoff, contains_service_catalog,
    contains_error_indicators, extract_ticket_number, detect_response_language
)


class TestResult:
    def __init__(self, scenario: dict):
        self.scenario = scenario
        self.test_id = scenario["id"]
        self.test_name = scenario["name"]
        self.category = scenario["category"]
        self.priority = scenario.get("priority", "medium")
        self.status = "pending"
        self.start_time = None
        self.end_time = None
        self.duration = 0
        self.conversation_log: List[Dict] = []
        self.validations_passed: List[str] = []
        self.validations_failed: List[str] = []
        self.ai_analysis: Dict = {}
        self.error_message = ""
        self.bugs_found: List[str] = []
        self.notes = ""

    def to_dict(self):
        return {
            "test_id": self.test_id, "test_name": self.test_name,
            "category": self.category, "priority": self.priority,
            "status": self.status,
            "start_time": str(self.start_time) if self.start_time else "",
            "end_time": str(self.end_time) if self.end_time else "",
            "duration": self.duration,
            "conversation_log": self.conversation_log,
            "validations_passed": self.validations_passed,
            "validations_failed": self.validations_failed,
            "ai_analysis": self.ai_analysis,
            "error_message": self.error_message,
            "bugs_found": self.bugs_found,
            "notes": self.notes,
        }


class TestEngine:
    def __init__(self):
        self.ai_brain = AIBrain()
        self.teams = TeamsAutomator()
        self.report_gen = ReportGenerator()
        self.results: List[TestResult] = []
        self.is_running = False
        self.should_stop = False
        self.current_test = ""
        self.total_tests = 0
        self.completed_tests = 0
        self.discovered_tickets: List[str] = []

    async def initialize(self, email: str, password: str) -> bool:
        try:
            await ws_manager.send_status("initializing", "Launching browser...")
            await self.teams.initialize()
            await ws_manager.send_status("logging_in", "Logging into Teams...")
            if not await self.teams.login(email, password):
                await ws_manager.send_status("error", "Login failed!")
                return False
            await ws_manager.send_status("opening_cva", "Opening CVA chat...")
            if not await self.teams.open_cva_chat():
                await ws_manager.send_status("error", "Could not open CVA!")
                return False
            await ws_manager.send_status("ready", "Ready!")
            return True
        except Exception as e:
            await ws_manager.send_status("error", f"Init failed: {str(e)}")
            return False

    async def run_all_tests(self, scenario_ids: List[str] = None):
        self.is_running = True
        self.should_stop = False
        self.results = []

        scenarios = get_all_scenarios()
        if scenario_ids:
            scenarios = [s for s in scenarios if s["id"] in scenario_ids]

        self.total_tests = len(scenarios)
        await ws_manager.send_status("running", f"Starting {self.total_tests} tests...")
        await ws_manager.send_log("info", f"🚀 Starting {self.total_tests} tests")

        for i, scenario in enumerate(scenarios):
            if self.should_stop: break
            self.current_test = scenario["name"]
            await ws_manager.send_progress(i + 1, self.total_tests, self.current_test)
            await ws_manager.send_log("info", f"━━━ [{scenario['id']}] {scenario['name']} ━━━")

            await self.teams.reset_chat_context()
            result = await self._run_test(scenario)
            self.results.append(result)
            self.completed_tests += 1

            await ws_manager.send_test_result(
                result.test_id, result.test_name, result.category,
                result.status, result.notes, result.error_message)

            if not self.should_stop and i < len(scenarios) - 1:
                await asyncio.sleep(5)

        if self.results:
            await ws_manager.send_status("generating_report", "Generating report...")
            report = self.report_gen.generate_excel_report(self.results)
            await ws_manager.send_log("info", f"📊 Report saved: {report}")

        p = sum(1 for r in self.results if r.status == "passed")
        f = sum(1 for r in self.results if r.status == "failed")
        e = sum(1 for r in self.results if r.status == "error")
        await ws_manager.send_status("completed", f"Done! ✅{p} ❌{f} ⚠️{e}")
        self.is_running = False

    async def run_journeys(self, sessions: int = 2):
        """
        Run 2 human-like sessions (journeys). Each journey is a sequence of scenarios
        executed in SAME Teams chat, simulating a real user who has multiple issues.
        """
        self.is_running = True
        self.should_stop = False
        self.results = []

        # Define journey as a sequence of scenario IDs (must exist in test_scenarios.py)
        journey_plan = [
            "INC-002",   # BSOD troubleshooting (multi-turn)
            "SR-001",    # Adobe install request
            "RET-001",   # unresolved/open tickets
            "RET-002",   # resolved/closed tickets
            "EDGE-001",  # gibberish
            "EDGE-002",  # password/reset help
        ]

        total_phases = sessions * len(journey_plan)
        await ws_manager.send_status("running", f"Running {sessions} human-like sessions ({total_phases} phases)...")
        await ws_manager.send_log("info", f"🧭 Starting Journey Mode: {sessions} sessions")

        phase_counter = 0

        for s_idx in range(1, sessions + 1):
            if self.should_stop:
                break

            await ws_manager.send_log("info", f"════════════════════════════════════")
            await ws_manager.send_log("info", f"🧭 Journey Session {s_idx}/{sessions} START")
            await ws_manager.send_log("info", f"════════════════════════════════════")

            # IMPORTANT: reset our local message baseline so we don't mis-detect delayed messages
            # This does NOT reset CVA context; it only resets our "seen hashes".
            await self.teams.reset_chat_context()

            # Optional: add a human-like bridge message at session start
            # (comment out if you don't want it)
            await self.teams.send_message("Hi, I need help with a few issues today.")
            await self.teams.wait_for_response(timeout=45)

            for scenario_id in journey_plan:
                if self.should_stop:
                    break

                # Find scenario by ID
                scenario = None
                for sc in get_all_scenarios():
                    if sc["id"] == scenario_id:
                        scenario = dict(sc)  # copy
                        break

                if not scenario:
                    await ws_manager.send_log("error", f"Scenario ID not found in test_scenarios.py: {scenario_id}")
                    continue

                # Make test_id unique per session so report doesn't have duplicate IDs
                scenario["id"] = f"J{s_idx}-{scenario['id']}"
                scenario["name"] = f"(Journey {s_idx}) {scenario['name']}"

                # IMPORTANT for human-like continuation: increase turns for some scenarios
                # so it doesn't stop after first helpful response.
                if "BSOD" in scenario["name"].upper() or "blue screen" in (scenario.get("description", "").lower()):
                    scenario["min_turns"] = max(scenario.get("min_turns", 1), 2)
                    scenario["max_turns"] = max(scenario.get("max_turns", 4), 4)

                # Progress update
                phase_counter += 1
                await ws_manager.send_progress(phase_counter, total_phases, scenario["name"])

                # Run phase as a normal test but DO NOT delay 5 seconds between phases
                await ws_manager.send_log("info", f"--- Journey Phase: {scenario['name']} ---")

                # Reset local baseline between phases to avoid delayed cards/text from polluting next phase
                await self.teams.reset_chat_context()

                result = await self._run_test(scenario)
                self.results.append(result)

                await ws_manager.send_test_result(
                    result.test_id, result.test_name, result.category,
                    result.status, result.notes, result.error_message
                )

        # Generate report
        if self.results:
            await ws_manager.send_status("generating_report", "Generating journey report...")
            report_path = self.report_gen.generate_excel_report(self.results)
            await ws_manager.send_log("info", f"📊 Journey report saved: {report_path}")

        # Summary
        p = sum(1 for r in self.results if r.status == "passed")
        f = sum(1 for r in self.results if r.status == "failed")
        e = sum(1 for r in self.results if r.status == "error")
        await ws_manager.send_status("completed", f"Journey done! ✅{p} ❌{f} ⚠️{e}")
        self.is_running = False

    async def _run_test(self, scenario: dict) -> TestResult:
        result = TestResult(scenario)
        result.start_time = datetime.now()

        try:
            conversation = []
            max_turns = scenario.get("max_turns", 4)
            min_turns = scenario.get("min_turns", 1)

            # Generate initial message
            initial = await self.ai_brain.generate_initial_message(scenario)
            await ws_manager.send_log("info", f"Message: {initial[:80]}")

            if not await self.teams.send_message(initial):
                result.status = "error"
                result.error_message = "Failed to send"
                return self._fin(result)

            conversation.append({"role": "user", "content": initial})
            result.conversation_log.append({"role": "user", "content": initial, "timestamp": timestamp_readable()})

            # Conversation loop
            for turn in range(1, max_turns + 1):
                if self.should_stop:
                    result.status = "stopped"
                    break

                await ws_manager.send_log("info", f"Turn {turn}: Waiting for CVA...")
                cva_response = await self.teams.wait_for_response()

                if not cva_response:
                    result.bugs_found.append(f"No response turn {turn}")
                    if turn == 1:
                        result.status = "failed"
                        result.error_message = "CVA did not respond"
                        return self._fin(result)
                    break

                conversation.append({"role": "assistant", "content": cva_response})
                result.conversation_log.append({"role": "assistant", "content": cva_response, "timestamp": timestamp_readable()})

                ticket = extract_ticket_number(cva_response)
                if ticket and ticket not in self.discovered_tickets:
                    self.discovered_tickets.append(ticket)
                    await ws_manager.send_log("info", f"🎫 Ticket: {ticket}")

                # Analyze
                analysis = await self.ai_brain.analyze_response(scenario, cva_response, conversation)
                result.ai_analysis = analysis

                # Check if we should stop the conversation
                goal_done = analysis.get("goal_achieved", False)
                should_continue = analysis.get("should_continue", True)

                # Don't end too early - ensure minimum turns for multi-step tests
                if goal_done and turn >= min_turns:
                    await ws_manager.send_log("info", "✅ Goal achieved!")
                    break

                if not should_continue and turn >= min_turns:
                    await ws_manager.send_log("info", "Analysis: conversation complete")
                    break

                # Generate follow-up
                if turn < max_turns:
                    follow_up = await self.ai_brain.generate_follow_up(
                        scenario, conversation, cva_response,
                        "achieved" if goal_done else "in_progress")

                    # Prevent duplicates
                    prev = [m["content"] for m in conversation if m["role"] == "user"]
                    attempts = 0
                    while follow_up in prev and attempts < 3:
                        follow_up = self.ai_brain._template_follow_up(scenario, conversation, cva_response)
                        attempts += 1

                    if follow_up in prev:
                        follow_up = "Can you help me further with this?"

                    await ws_manager.send_log("info", f"Turn {turn+1}: {follow_up[:80]}")
                    if not await self.teams.send_message(follow_up):
                        break

                    conversation.append({"role": "user", "content": follow_up})
                    result.conversation_log.append({"role": "user", "content": follow_up, "timestamp": timestamp_readable()})

            self._validate(result, conversation)

            if result.status == "stopped":
                pass
            elif result.validations_failed:
                result.status = "failed"
                result.notes = f"Failed: {', '.join(result.validations_failed[:3])}"
            else:
                result.status = "passed"
                result.notes = f"Passed {len(result.validations_passed)} checks"

        except Exception as e:
            result.status = "error"
            result.error_message = str(e)

        return self._fin(result)

    def _fin(self, result):
        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()
        e = {"passed": "✅", "failed": "❌", "error": "⚠️", "stopped": "⏹️"}.get(result.status, "❓")
        asyncio.ensure_future(ws_manager.send_log("info", f"{e} {result.test_id}: {result.status} ({result.duration:.1f}s)"))
        return result

    def _validate(self, result, conversation):
        validations = result.scenario.get("validations", [])
        all_cva = " ".join(m["content"] for m in conversation if m["role"] == "assistant")
        cva = all_cva.lower()

        for v in validations:
            passed = False
            if v == "provides_troubleshooting_steps":
                passed = any(w in cva for w in ["step", "try", "check", "restart", "1.", "troubleshoot"])
            elif v == "includes_citations":
                passed = contains_citation(all_cva)
            elif v == "asks_follow_up_questions":
                passed = "?" in all_cva
            elif v == "creates_incident":
                passed = contains_ticket_confirmation(all_cva)
            elif v == "returns_inc_number":
                passed = bool(extract_ticket_number(all_cva))
            elif v == "shows_ticket_details":
                passed = any(w in cva for w in ["subject:", "description:", "status:", "incident number"])
            elif v == "shows_servicenow_link":
                passed = any(w in cva for w in ["servicenow", "view ticket", "view your ticket", "view in servicenow"])
            elif v == "shows_catalog_item":
                passed = contains_service_catalog(all_cva) or "adaptive card" in cva
            elif v == "detects_service_request":
                passed = any(w in cva for w in ["service", "catalog", "ritm", "adaptive card"])
            elif v in ("shows_ticket_list", "includes_inc_numbers"):
                passed = contains_ticket_list(all_cva)
            elif v == "initiates_handoff":
                passed = contains_live_agent_handoff(all_cva)
            elif v in ("detects_language", "responds_in_same_language"):
                passed = detect_response_language(all_cva) != "English"
            elif v in ("handles_gracefully", "no_error_crash"):
                passed = not contains_error_indicators(all_cva) and len(all_cva) > 10
            elif v == "warns_about_sensitive_data":
                passed = any(w in cva for w in ["password", "sensitive", "don't share", "security"])
            elif v == "maintains_context":
                passed = len(conversation) >= 4
            else:
                passed = True

            if passed:
                result.validations_passed.append(v)
            else:
                result.validations_failed.append(v)
                result.bugs_found.append(f"Failed: {v}")

    async def stop_tests(self):
        self.should_stop = True
        await ws_manager.send_log("warning", "⏹️ Stopping...")

    async def cleanup(self):
        await self.ai_brain.close()
        await self.teams.close()

    def get_results_summary(self):
        t = len(self.results)
        p = sum(1 for r in self.results if r.status == "passed")
        f = sum(1 for r in self.results if r.status == "failed")
        e = sum(1 for r in self.results if r.status == "error")
        return {"total": t, "passed": p, "failed": f, "errors": e,
                "pass_rate": round((p/t)*100, 1) if t else 0,
                "results": [r.to_dict() for r in self.results],
                "discovered_tickets": self.discovered_tickets}
