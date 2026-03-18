"""
Test Engine - stabilized structured runner
"""
import asyncio
import os
import re
import difflib
import time
from datetime import datetime
from typing import List, Dict, Optional

from config import app_config
from ai_brain import AIBrain
from teams_automator import TeamsAutomator
from test_scenarios import get_all_scenarios
from report_generator import ReportGenerator
from websocket_manager import ws_manager

from utils import (
    timestamp_readable,
    extract_ticket_number,
)

from validators.validator_factory import ValidatorFactory
from bug_analyzer import BugAnalyzer
from execution_mode_helpers import should_skip_for_manual, should_warn_for_partial
from run_guard import RunGuard
from dependency_resolver import DependencyResolver
from structured_prompt_builder import StructuredPromptBuilder
from structured_prompt_overrides import StructuredPromptOverrides
from structured_execution_profile import StructuredExecutionProfile
from structured_followup_v2 import StructuredFollowUpV2
from structured_goal_checker import StructuredGoalChecker
from structured_turn_policy import StructuredTurnPolicy
from structured_result_fixer import StructuredResultFixer
from structured_runtime_state import StructuredRuntimeState
from attachment_runtime_state import AttachmentRuntimeState
from attachment_context_manager import AttachmentContextManager
from ticket_context_manager import TicketContextManager
from ticket_followup_builder import TicketFollowUpBuilder
from attachment_reply_guard import AttachmentReplyGuard
from structured_outcome_resolver import StructuredOutcomeResolver
from conversation_interruptions import ConversationInterruptions
from recovery_strategy import RecoveryStrategy
from teams_attachment_debugger import TeamsAttachmentDebugger
from qa_scoring import QAScoring
from structured_family_validator import StructuredFamilyValidator
from structured_result_enricher import StructuredResultEnricher


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
        self.kb_links_found: List[str] = []

        self.lifecycle = {
            "intent": scenario.get("intent"),
            "stage": "start",
            "ticket_id": None,
        }

        self.state = {
            "ticket_created": False,
            "ticket_updated": False,
            "ticket_resolved": False,
            "ticket_closed": False,
        }

        self.final_status = ""
        self.semantic_score = 0
        self.ai_intent_match = ""
        self.failure_type = ""
        self.api_mode = "Fallback Mode"

        self.execution_mode = scenario.get("execution_mode", "")
        self.automation_level = scenario.get("automation_level", "full")

        self.structured_family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "") or "")
        self.alternate_outcome = False
        self.alternate_reason = ""
        self.goal_achieved_reason = ""

        self.qa_score = 0
        self.qa_grade = ""
        self.display_status = ""

        self.attachment_upload_succeeded = False
        self.attachment_uploaded_files = []

        excel = scenario.get("excel") or {}
        self.client = excel.get("client", "")
        self.module = excel.get("module", "")
        self.action = excel.get("action", "")
        self.source_kb = excel.get("source_kb", "")

        self.excel_client = excel.get("client", "")
        self.excel_module = excel.get("module", "")
        self.excel_action = excel.get("action", "")
        self.excel_source_kb = excel.get("source_kb", "")
        self.excel_expected_response = excel.get("expected_response", "")
        self.excel_tool_calling = excel.get("tool_calling_queries", False)
        self.excel_user_query = excel.get("user_query", scenario.get("initial_message", ""))

        self.actual_first_reply = ""
        self.actual_last_reply = ""
        self.expected_similarity = None
        self.expected_judge = None

    def to_dict(self):
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "category": self.category,
            "priority": self.priority,
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
            "kb_links_found": self.kb_links_found,
            "state": self.state,
            "lifecycle": self.lifecycle,
            "final_status": self.final_status,
            "semantic_score": self.semantic_score,
            "ai_intent_match": self.ai_intent_match,
            "failure_type": self.failure_type,
            "api_mode": self.api_mode,
            "execution_mode": self.execution_mode,
            "automation_level": self.automation_level,
            "structured_family": self.structured_family,
            "alternate_outcome": self.alternate_outcome,
            "alternate_reason": self.alternate_reason,
            "goal_achieved_reason": self.goal_achieved_reason,
            "qa_score": self.qa_score,
            "qa_grade": self.qa_grade,
            "display_status": self.display_status,
        }


def calculate_score(deterministic_pass, semantic_score):
    if deterministic_pass and semantic_score >= 8:
        return "PASS"
    if deterministic_pass and semantic_score >= 5:
        return "PASS_WITH_WARNING"
    if not deterministic_pass and semantic_score >= 8:
        return "REVIEW"
    return "FAIL"


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
        self.confirmed_tickets: List[str] = []

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

    async def run_all_tests(self, scenario_ids: Optional[List[str]] = None):
        from history import record_run

        self.is_running = True
        self.should_stop = False
        start_time = time.time()
        await ws_manager.send_log("info", "🚀 Starting test run...")

        try:
            self.results = await self._run_all_tests(scenario_ids)
            record_run(self.results)
        except Exception as e:
            await ws_manager.send_log("error", f"Test run failed: {e}")
        finally:
            self.is_running = False
            elapsed = time.time() - start_time
            await ws_manager.send_log("info", f"✅ Test run completed in {elapsed:.1f}s")

    async def _run_all_tests(self, scenario_ids: Optional[List[str]] = None):
        scenarios = get_all_scenarios()
        if scenario_ids:
            scenarios = [s for s in scenarios if s["id"] in scenario_ids]

        self.total_tests = len(scenarios)
        await ws_manager.send_status("running", f"Starting {self.total_tests} tests...")
        await ws_manager.send_log("info", f"🚀 Starting {self.total_tests} tests")

        self.results = []
        self.completed_tests = 0

        for i, scenario in enumerate(scenarios):
            if self.should_stop:
                break

            self.current_test = scenario["name"]
            await ws_manager.send_progress(i + 1, self.total_tests, self.current_test)
            await ws_manager.send_log("info", f"━━━ [{scenario['id']}] {scenario['name']} ━━━")

            await self.teams.reset_chat_context()
            result = await self._run_test(scenario)

            self.results.append(result)
            self.completed_tests += 1

            await ws_manager.send_test_result(
                result.test_id,
                result.test_name,
                result.category,
                result.status,
                result.notes,
                result.error_message,
            )

            if not self.should_stop and i < len(scenarios) - 1:
                await asyncio.sleep(2)

        if self.results:
            await ws_manager.send_status("generating_report", "Generating report...")
            report = self.report_gen.generate_excel_report(self.results)
            await ws_manager.send_log("info", f"📊 Report saved: {report}")

        p = sum(1 for r in self.results if r.status == "passed")
        f = sum(1 for r in self.results if r.status == "failed")
        e = sum(1 for r in self.results if r.status == "error")
        s = sum(1 for r in self.results if r.status == "skipped")
        await ws_manager.send_status("completed", f"Done! ✅{p} ❌{f} ⚠️{e} ⏭️{s}")
        self.is_running = False

    async def run_custom_suite(self, scenarios: List[dict], suite_name: str = "Custom Suite"):
        self.is_running = True
        self.should_stop = False
        self.results = []
        self.completed_tests = 0
        self.total_tests = len(scenarios)

        await ws_manager.send_status("running", f"Running suite: {suite_name} ({self.total_tests} tests)...")
        await ws_manager.send_log("info", f"📄 Running custom suite: {suite_name} ({self.total_tests} tests)")

        for i, scenario in enumerate(scenarios):
            if self.should_stop:
                break

            self.current_test = scenario["name"]
            await ws_manager.send_progress(i + 1, self.total_tests, self.current_test)
            await ws_manager.send_log("info", f"━━━ [{scenario['id']}] {scenario['name']} ━━━")

            await self.teams.reset_chat_context()
            result = await self._run_test(scenario)
            self.results.append(result)
            self.completed_tests += 1

            await ws_manager.send_test_result(
                result.test_id, result.test_name, result.category,
                result.status, result.notes, result.error_message
            )

            if not self.should_stop and i < len(scenarios) - 1:
                await asyncio.sleep(2)

        if self.results:
            await ws_manager.send_status("generating_report", "Generating report...")
            report = self.report_gen.generate_excel_report(self.results)
            await ws_manager.send_log("info", f"📊 Report saved: {report}")

        p = sum(1 for r in self.results if r.status == "passed")
        f = sum(1 for r in self.results if r.status == "failed")
        e = sum(1 for r in self.results if r.status == "error")
        s = sum(1 for r in self.results if r.status == "skipped")
        await ws_manager.send_status("completed", f"Suite done! ✅{p} ❌{f} ⚠️{e} ⏭️{s}")
        self.is_running = False

    async def _run_test(self, scenario: dict) -> TestResult:
        result = TestResult(scenario)
        result = StructuredRuntimeState.ensure(result)
        result = AttachmentRuntimeState.ensure(result)
        result.start_time = datetime.now()

        try:
            conversation = []

            await ws_manager.send_log(
                "info",
                f"Execution mode={scenario.get('execution_mode', 'legacy')} | automation={scenario.get('automation_level', 'full')}"
            )

            if should_skip_for_manual(scenario):
                result.status = "skipped"
                result.notes = "Skipped: scenario marked manual-only by structured planner"
                result.final_status = "MANUAL"
                return self._fin(result)

            skip_reason = RunGuard.should_skip(scenario)
            if skip_reason:
                result.status = "skipped"
                result.notes = skip_reason
                result.final_status = "MANUAL"
                return self._fin(result)

            if scenario.get("execution_mode") and not StructuredExecutionProfile.is_supported_now(scenario):
                result.status = "skipped"
                result.notes = StructuredExecutionProfile.reason_unsupported(scenario)
                result.final_status = "UNSUPPORTED"
                return self._fin(result)

            scenario = DependencyResolver.apply_runtime_context(scenario, self.confirmed_tickets or self.discovered_tickets)

            chosen_ticket = TicketContextManager.choose_ticket_for_scenario(
                scenario,
                self.confirmed_tickets,
                self.discovered_tickets
            )
            scenario = TicketContextManager.inject_ticket_into_scenario(scenario, chosen_ticket)

            synthesized = TicketContextManager.build_ticket_intent_message(scenario, chosen_ticket)
            if synthesized and not (scenario.get("initial_message") or "").strip():
                scenario["initial_message"] = synthesized
                scenario.setdefault("excel", {})
                scenario["excel"]["user_query"] = synthesized

            if ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower() == "attachment":
                attach_ticket = AttachmentContextManager.choose_ticket_for_attachment(
                    self.confirmed_tickets,
                    self.discovered_tickets
                )
                scenario = AttachmentContextManager.inject_attachment_ticket_context(scenario, attach_ticket)
                built = AttachmentContextManager.build_attachment_initial_message(scenario, attach_ticket)
                if built:
                    scenario["initial_message"] = built
                    scenario.setdefault("excel", {})
                    scenario["excel"]["user_query"] = built
                result.lifecycle["ticket_id"] = attach_ticket

            scenario = StructuredPromptOverrides.apply(scenario)
            result.structured_family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "") or "")

            if DependencyResolver.needs_ticket_but_missing(scenario, self.confirmed_tickets or self.discovered_tickets):
                result.status = "skipped"
                result.notes = "Skipped: scenario requires a real ticket context but none is available yet"
                result.final_status = "BLOCKED"
                return self._fin(result)

            if scenario.get("execution_mode"):
                ai_initial = await self.ai_brain.generate_structured_initial_message(scenario)
                if ai_initial and len(ai_initial.strip()) > 3:
                    scenario["initial_message"] = ai_initial
                    scenario.setdefault("excel", {})
                    scenario["excel"]["user_query"] = ai_initial
                else:
                    if not (scenario.get("initial_message") or "").strip():
                        scenario["initial_message"] = StructuredPromptBuilder.build_initial_message(scenario)
                        scenario.setdefault("excel", {})
                        scenario["excel"]["user_query"] = scenario["initial_message"]
            else:
                if not (scenario.get("initial_message") or "").strip():
                    scenario["initial_message"] = StructuredPromptBuilder.build_initial_message(scenario)
                    scenario.setdefault("excel", {})
                    scenario["excel"]["user_query"] = scenario["initial_message"]

            max_turns = scenario.get("max_turns", 4)
            min_turns = scenario.get("min_turns", 1)

            if scenario.get("execution_mode"):
                max_turns = StructuredTurnPolicy.max_turns_for(scenario)
                if StructuredTurnPolicy.should_stop_after_first_response(scenario):
                    scenario["stop_after_first_response"] = True
                    min_turns = 1

            initial = scenario.get("initial_message") or await self.ai_brain.generate_initial_message(scenario)
            await ws_manager.send_log("info", f"Message: {initial[:120]}")

            if not await self.teams.send_message(initial):
                result.status = "error"
                result.error_message = "Failed to send"
                return self._fin(result)

            conversation.append({"role": "user", "content": initial})
            result.conversation_log.append({"role": "user", "content": initial, "timestamp": timestamp_readable()})

            for turn in range(1, max_turns + 1):
                if self.should_stop:
                    result.status = "stopped"
                    break

                await ws_manager.send_log("info", f"Turn {turn}: Waiting for CVA...")
                cva_response = await self.teams.wait_for_response(timeout=scenario.get("response_timeout"))

                if not cva_response:
                    await ws_manager.send_log("warning", "Timeout hit; doing late-reply sweep (15s)...")
                    late = await self.teams.wait_for_response(timeout=15)
                    if late:
                        cva_response = late
                        await ws_manager.send_log("info", "✅ Late reply found!")
                    else:
                        result.bugs_found.append(f"No response turn {turn}")
                        if turn == 1:
                            result.status = "failed"
                            result.error_message = "CVA did not respond (timeout)"
                            return self._fin(result)
                        break

                links = self.teams.last_response_links or []
                if links:
                    for u in links:
                        if u and u not in result.kb_links_found:
                            result.kb_links_found.append(u)

                conversation.append({"role": "assistant", "content": cva_response, "links": links})
                result.conversation_log.append({
                    "role": "assistant",
                    "content": cva_response,
                    "timestamp": timestamp_readable(),
                    "links": links,
                })

                if scenario.get("execution_mode") and ConversationInterruptions.is_interruption(cva_response):
                    await ws_manager.send_log("warning", "Structured interruption detected (session expiry / restart notice)")
                    if turn < max_turns:
                        recovery_msg = RecoveryStrategy.recover_message_for_interruption(scenario, conversation)
                        await ws_manager.send_log("info", f"Recovery message: {recovery_msg[:120]}")
                        ok = await self.teams.send_message(recovery_msg)
                        if ok:
                            conversation.append({"role": "user", "content": recovery_msg})
                            result.conversation_log.append({
                                "role": "user",
                                "content": recovery_msg,
                                "timestamp": timestamp_readable()
                            })
                            continue
                    else:
                        result.bugs_found.append("Session interruption occurred and no turns remained for recovery")
                        break

                if not result.actual_first_reply:
                    result.actual_first_reply = cva_response
                result.actual_last_reply = cva_response

                if result.scenario.get("stop_after_first_response") and turn >= 1:
                    await ws_manager.send_log("info", "Stopping after first response (single-turn / structured stop policy).")
                    break

                ticket = extract_ticket_number(cva_response)
                if ticket:
                    scenario["context_ticket_id"] = ticket
                    if ticket not in self.discovered_tickets:
                        self.discovered_tickets.append(ticket)
                        await ws_manager.send_log("info", f"🎫 Ticket seen: {ticket}")

                cva_low = (cva_response or "").lower()
                if ticket:
                    result.lifecycle["ticket_id"] = ticket

                if "created" in cva_low:
                    result.lifecycle["stage"] = "created"
                elif "updated" in cva_low:
                    result.lifecycle["stage"] = "updated"
                elif "closed" in cva_low:
                    result.lifecycle["stage"] = "closed"
                elif "resolved" in cva_low:
                    result.lifecycle["stage"] = "resolved"

                if "access denied" in cva_low:
                    result.status = "failed"
                    result.bugs_found.append("Access denied for ticket operation.")
                    break

                if ticket:
                    if any(k in cva_low for k in [
                        "ticket has been successfully created",
                        "ticket has been created",
                        "incident ticket created",
                        "ticket details",
                        "here are your open tickets",
                        "here are your current open tickets",
                    ]):
                        if ticket not in self.confirmed_tickets:
                            self.confirmed_tickets.append(ticket)
                            await ws_manager.send_log("info", f"✅ Ticket confirmed: {ticket}")

                analysis = await self.ai_brain.analyze_response(scenario, cva_response, conversation)
                result.ai_analysis = analysis

                if scenario.get("execution_mode"):
                    goal_done, goal_reason = StructuredGoalChecker.check_goal(scenario, cva_response, links)
                    result.goal_achieved_reason = goal_reason or ""
                    result.ai_analysis["goal_achieved"] = goal_done
                    result.ai_analysis["goal_reason"] = goal_reason or ""
                    result.ai_analysis["should_continue"] = not goal_done
                    result.ai_analysis["has_error"] = False
                    result.ai_analysis["notes"] = f"Structured mode: {scenario.get('execution_mode', '')}"

                    if goal_done and turn >= min_turns:
                        await ws_manager.send_log("info", f"✅ Structured goal achieved: {goal_reason}")
                        break
                else:
                    goal_done = analysis.get("goal_achieved", False)

                should_continue = analysis.get("should_continue", True)

                if goal_done and turn >= min_turns:
                    break

                if not should_continue and turn >= min_turns:
                    await ws_manager.send_log("info", "Analysis: conversation complete")
                    break

                if turn < max_turns:
                    attachments = None
                    follow_up = ""

                    if scenario.get("execution_mode"):
                        ticket_id = scenario.get("context_ticket_id", "")
                        family = ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower()

                        if family == "attachment":
                            follow_up = AttachmentReplyGuard.build_reply(
                                scenario=scenario,
                                cva_response=cva_response,
                                ticket_id=ticket_id,
                                uploaded_files=result.attachment_uploaded_files,
                                upload_succeeded=result.attachment_upload_succeeded
                            )
                            if not follow_up or len(follow_up.strip()) < 3:
                                follow_up = StructuredFollowUpV2.next_user_reply(scenario, conversation, cva_response)
                        else:
                            follow_up = TicketFollowUpBuilder.build(scenario, cva_response, ticket_id=ticket_id)

                            if not follow_up or len(follow_up.strip()) < 3:
                                follow_up = await self.ai_brain.generate_structured_follow_up(
                                    scenario, conversation, cva_response
                                )

                            if not follow_up or len(follow_up.strip()) < 3:
                                follow_up = StructuredFollowUpV2.next_user_reply(scenario, conversation, cva_response)

                    if not follow_up or len(follow_up.strip()) < 3:
                        follow_up = await self.ai_brain.generate_follow_up(
                            scenario, conversation, cva_response,
                            "achieved" if goal_done else "in_progress"
                        )

                    prev = [m["content"] for m in conversation if m["role"] == "user"]
                    if follow_up in prev:
                        if scenario.get("execution_mode"):
                            follow_up = "The issue is still happening and I need help with the next step."
                        else:
                            follow_up = "I tried that but it didn't fix it. What should I do next?"

                    await ws_manager.send_log("info", f"Turn {turn+1}: {follow_up[:120]}")

                    if attachments:
                        uploaded = await self.teams.upload_attachments(attachments)
                        if not uploaded:
                            result.status = "failed"
                            result.bugs_found.append(TeamsAttachmentDebugger.summarize_failure())
                            result.error_message = "Attachment upload failed"
                            return self._fin(result)
                        result.attachment_upload_succeeded = True
                        result.attachment_uploaded_files = [str(x) for x in attachments]
                        scenario["uploaded_file_names"] = [str(x).split("/")[-1] for x in attachments]

                    elif ((scenario.get("excel", {}) or {}).get("family", "") or scenario.get("family", "")).lower() == "attachment":
                        staged = app_config.staged_attachments or []
                        if staged:
                            uploaded = await self.teams.upload_attachments(staged)
                            if not uploaded:
                                result.status = "failed"
                                result.bugs_found.append(TeamsAttachmentDebugger.summarize_failure())
                                result.error_message = "Attachment upload failed"
                                return self._fin(result)
                            result.attachment_upload_succeeded = True
                            result.attachment_uploaded_files = [str(x) for x in staged]
                            scenario["uploaded_file_names"] = [str(x).split("/")[-1] for x in staged]

                    ok = await self.teams.send_message(follow_up)
                    if not ok:
                        result.bugs_found.append("Failed to send follow-up")
                        break

                    conversation.append({"role": "user", "content": follow_up})
                    result.conversation_log.append({"role": "user", "content": follow_up, "timestamp": timestamp_readable()})

            await self._check_expected_response(result, conversation)
            validation = await self._validate(result, conversation)

            semantic_score = 0
            judge = None
            expected_response = (result.scenario.get("excel", {}) or {}).get("expected_response", "")
            # Only call AI judge when there's an expected response to compare
            if self.ai_brain.is_available() and expected_response and expected_response.strip():
                judge = await self.ai_brain.judge_expected(
                    result.scenario.get("initial_message", ""),
                    result.actual_first_reply or "",
                    expected_response
                )
                semantic_score = judge.get("relevance", 0)
            elif self.ai_brain.is_available():
                # No expected response defined — give neutral score, skip judge
                semantic_score = 5
                judge = {"matches": True, "relevance": 5, "reason": "No expected response defined; skipped AI judge"}

            result.semantic_score = semantic_score
            result.ai_intent_match = judge.get("matches", "") if judge else ""
            result.api_mode = "AI Active" if self.ai_brain.is_available() else "Fallback Mode"
            result.failure_type = result.status if result.status == "failed" else ""

            if result.scenario.get("execution_mode"):
                result.final_status = "PASS" if validation["passed"] else "FAIL"
            else:
                result.final_status = calculate_score(validation["passed"], semantic_score)

            if result.status == "stopped":
                pass
            elif result.validations_failed:
                result.status = "failed"
                if scenario.get("execution_mode"):
                    if result.alternate_outcome and result.alternate_reason:
                        result.notes = f"Incomplete structured workflow: {result.alternate_reason}"
                    elif not (result.notes and result.notes.lower().startswith("structured validation failed")):
                        result.notes = f"Failed: {', '.join(result.validations_failed[:3])}"
                else:
                    result.notes = f"Failed: {', '.join(result.validations_failed[:3])}"
            else:
                result.status = "passed"
                if not (scenario.get("execution_mode") and result.notes and (
                    result.notes.lower().startswith("structured validation") or
                    result.notes.lower().startswith("structured workflow") or
                    result.notes.lower().startswith("passed via acceptable alternate")
                )):
                    result.notes = f"Passed {len(result.validations_passed)} checks"

                if should_warn_for_partial(scenario) and result.final_status == "PASS":
                    result.final_status = "PASS_WITH_WARNING"
                    result.notes = f"{result.notes} | Partial-automation scenario"

        except Exception as e:
            result.status = "error"
            result.error_message = str(e)

        seen = set()
        deduped = []
        for b in result.bugs_found:
            key = (b or "").strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(key)
        result.bugs_found = deduped

        if not result.failure_type:
            result.failure_type = BugAnalyzer.classify(result.validations_failed, result.error_message)

        if result.scenario.get("execution_mode"):
            family = ((result.scenario.get("excel", {}) or {}).get("family", "") or result.scenario.get("family", "")).lower()

            if result.status == "failed" and "attachment upload failed" in (result.error_message or "").lower():
                result.failure_type = "Automation Limitation / Attachment Upload"

            elif result.status == "failed" and result.validations_failed:
                result.failure_type = f"Structured Validation Failure ({family or 'unknown'})"

            elif result.status == "passed" and result.final_status == "PASS_WITH_WARNING":
                result.failure_type = f"Warning / Partial Recovery ({family or 'unknown'})"

            elif result.status == "skipped":
                result.failure_type = "Blocked / Manual / Unsupported"

        if result.scenario.get("execution_mode"):
            outcome = StructuredOutcomeResolver.resolve(result)

            result.alternate_outcome = False
            result.alternate_reason = ""

            if outcome.get("ticket_id"):
                result.lifecycle["ticket_id"] = outcome["ticket_id"]

            final_path = outcome.get("final_path", "")
            notes = outcome.get("notes", []) or []
            alternate_reason = outcome.get("alternate_reason", "") or ""

            if final_path == "new_ticket_created":
                result.alternate_outcome = False
                result.alternate_reason = ""
                result.goal_achieved_reason = "New incident created"
                result.final_status = "PASS"
                if notes:
                    result.notes = f"Structured validation passed: {notes[0]}"

            elif final_path == "existing_ticket_updated":
                family = ((result.scenario.get("excel", {}) or {}).get("family", "") or result.scenario.get("family", "")).lower()

                if family == "ticket_update":
                    result.alternate_outcome = False
                    result.alternate_reason = ""
                    result.goal_achieved_reason = "Ticket updated"
                    result.final_status = "PASS"
                    result.notes = f"Structured validation passed: {notes[0] if notes else 'Ticket updated'}"

                elif family == "ticket_create":
                    result.alternate_outcome = True
                    result.alternate_reason = alternate_reason or "Existing ticket updated instead of creating a duplicate"
                    result.goal_achieved_reason = "Existing related incident reused/updated instead of duplicate creation"
                    result.final_status = "PASS_WITH_WARNING"
                    result.notes = f"Passed via acceptable alternate outcome: {result.alternate_reason}"

                else:
                    result.alternate_outcome = False
                    result.alternate_reason = ""
                    result.goal_achieved_reason = "Ticket updated"
                    result.final_status = "PASS"
                    result.notes = f"Structured validation passed: {notes[0] if notes else 'Ticket updated'}"

            elif final_path == "ticket_updated":
                result.alternate_outcome = False
                result.alternate_reason = ""
                result.goal_achieved_reason = "Ticket updated"
                result.final_status = "PASS"
                if notes:
                    result.notes = f"Structured validation passed: {notes[0]}"

            elif final_path == "ticket_list_retrieved":
                result.alternate_outcome = False
                result.alternate_reason = ""
                result.goal_achieved_reason = "Open ticket list retrieved"
                result.final_status = "PASS"
                if notes:
                    result.notes = f"Structured validation passed: {notes[0]}"
                if outcome.get("ticket_id"):
                    result.lifecycle["ticket_id"] = outcome["ticket_id"]

            elif final_path == "ticket_closed":
                result.alternate_outcome = False
                result.alternate_reason = ""
                result.goal_achieved_reason = "Ticket closed"
                result.final_status = "PASS"
                if notes:
                    result.notes = f"Structured validation passed: {notes[0]}"

            elif final_path == "attachment_handled":
                result.alternate_outcome = False
                result.alternate_reason = ""
                result.goal_achieved_reason = "Attachment handled"
                result.final_status = "PASS"
                if notes:
                    result.notes = f"Structured validation passed: {notes[0]}"

            elif final_path == "slot_filling_only":
                result.alternate_outcome = True
                result.alternate_reason = alternate_reason or "Valid workflow started, but final ticket action did not complete yet"
                result.goal_achieved_reason = ""
                if result.status == "passed":
                    result.final_status = "PASS_WITH_WARNING"
                result.notes = f"Incomplete structured workflow: {result.alternate_reason}"

        result = StructuredResultFixer.normalize(result)

        if result.scenario.get("execution_mode") and result.alternate_outcome and result.status == "passed":
            result.final_status = "PASS_WITH_WARNING"

        score_data = QAScoring.calculate(result)
        result.qa_score = score_data["qa_score"]
        result.qa_grade = score_data["qa_grade"]
        result.display_status = score_data["display_status"]

        return self._fin(result)

    async def _check_expected_response(self, result: TestResult, conversation: List[Dict]):
        excel = (result.scenario.get("excel") or {})
        module = (excel.get("module") or "").lower()

        if module in ["greeting / closing", "out-of-scope"]:
            return

        expected = (excel.get("expected_response") or "").strip()
        if not expected:
            return

        first_bot = ""
        for m in conversation:
            if m.get("role") == "assistant":
                first_bot = (m.get("content") or "")
                break

        if not first_bot.strip():
            result.validations_failed.append("matches_expected_semantic")
            result.bugs_found.append("Expected-response check failed: no CVA reply to compare.")
            return

        def norm(s: str) -> str:
            s = (s or "").lower()
            s = re.sub(r"\s+", " ", s).strip()
            return s

        sim = difflib.SequenceMatcher(None, norm(expected), norm(first_bot)).ratio()
        result.expected_similarity = round(sim, 3)
        result.ai_analysis["expected_similarity"] = round(sim, 3)

        if not getattr(self.ai_brain, "_working_model", None):
            if sim >= 0.55:
                result.validations_passed.append("matches_expected_semantic")
                result.ai_analysis["expected_judge"] = {"matches": True, "reason": f"Similarity >= 0.55 without judge (sim={sim:.3f})"}
            else:
                result.validations_passed.append("skipped_judge")
                result.bugs_found.append(
                    f"Judge unavailable. Cannot verify Expected Response semantically. similarity={sim:.2f}"
                )
            return

        if sim >= 0.55:
            result.validations_passed.append("matches_expected_semantic")
            result.ai_analysis["expected_judge"] = {"matches": True, "reason": f"Similarity >= 0.55 (sim={sim:.3f})"}
            return

        judge = await self.ai_brain.judge_expected(
            user_query=excel.get("user_query") or result.scenario.get("initial_message", ""),
            cva_response=first_bot,
            expected=expected,
            action=excel.get("action", ""),
        )
        result.expected_judge = judge
        result.ai_analysis["expected_judge"] = judge

        reason = (judge.get("reason") or "").lower()
        if (not judge) or ("empty response" in reason) or ("judge unavailable" in reason) or ("non-json" in reason):
            result.validations_passed.append("skipped_judge")
            result.bugs_found.append(f"Judge unavailable/failed; cannot verify Expected Response. similarity={sim:.2f}")
            return

        if judge.get("matches"):
            result.validations_passed.append("matches_expected_semantic")
        else:
            result.validations_failed.append("matches_expected_semantic")
            result.bugs_found.append(f"Expected response mismatch (sim={sim:.2f}): {judge.get('reason','')}")

    def _fin(self, result):
        result.end_time = datetime.now()
        result.duration = (result.end_time - result.start_time).total_seconds()
        return result

    async def _validate(self, result: TestResult, conversation: List[Dict]):
        validation_result = await self._validate_with_semantic_fallback(result, conversation)
        if isinstance(validation_result, dict):
            return validation_result
        return {"passed": False, "failures": ["Validation error"], "notes": []}

    async def _validate_with_semantic_fallback(self, result: TestResult, conversation: List[Dict]):
        if result.scenario.get("execution_mode"):
            validation = StructuredFamilyValidator.validate(result)

            result.validations_passed.clear()
            result.validations_failed.clear()

            if validation["passed"]:
                result.validations_passed.append("structured_validation_passed")
            else:
                for f in validation["failures"]:
                    if f not in result.validations_failed:
                        result.validations_failed.append(f)
                        result.bugs_found.append(f)

            result = StructuredResultEnricher.apply(result, validation)
            return validation

        module = result.scenario.get("category", "")
        validator = ValidatorFactory.get_validator(module, result.scenario)

        validation = validator.validate(result, conversation)

        result.validations_passed.clear()
        result.validations_failed.clear()

        if validation["passed"]:
            result.validations_passed.append("module_validation_passed")
            result.notes = "Validation passed"
        else:
            for f in validation["failures"]:
                if f not in result.validations_failed:
                    result.validations_failed.append(f)
                    result.bugs_found.append(f)
            result.notes = "Validation failed"

        if not validation["passed"]:
            expected = (result.scenario.get("excel", {}) or {}).get("expected_response", "")
            if expected and self.ai_brain.is_available():
                judge = await self.ai_brain.judge_expected(
                    user_query=result.scenario.get("excel", {}).get("user_query", ""),
                    cva_response=result.actual_first_reply,
                    expected=expected,
                    action=result.scenario.get("excel", {}).get("action", "")
                )

                if judge.get("matches"):
                    result.status = "passed"
                    result.notes = "Passed via semantic validation"
                    return {"passed": True, "failures": [], "notes": ["Passed via semantic validation"]}

        return validation

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
        s = sum(1 for r in self.results if r.status == "skipped")
        return {
            "total": t,
            "passed": p,
            "failed": f,
            "errors": e,
            "skipped": s,
            "pass_rate": round((p / t) * 100, 1) if t else 0,
            "results": [r.to_dict() for r in self.results],
            "discovered_tickets": self.discovered_tickets,
        }
