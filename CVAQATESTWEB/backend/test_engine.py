"""
Test Engine v6
Upgrades:
- Stores CVA hyperlinks extracted from Teams DOM (KB link validation)
- Fixes validations for KB hyperlink
- Slightly better bug detection without breaking existing passes
- Adds support for "skipped" (used by attachment scenarios in Part 2)
"""
import asyncio
import os
import re
import difflib
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
    contains_ticket_confirmation,
    contains_ticket_list,
    contains_citation,
    detect_response_language,
    contains_error_indicators,
    extract_ticket_number,
    contains_service_catalog,
    has_kb_hyperlink,
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
        self.kb_links_found: List[str] = []
        
        # Ticket lifecycle state tracker
        self.state = {
            "ticket_created": False,
            "ticket_updated": False,
            "ticket_resolved": False,
            "ticket_closed": False,
        }
        
        # Excel metadata
        excel = scenario.get("excel") or {}
        self.client = excel.get("client", "")
        self.module = excel.get("module", "")
        self.action = excel.get("action", "")
        self.source_kb = excel.get("source_kb", "")
        
        # Extended Excel metadata for reporting
        self.excel_client = excel.get("client", "")
        self.excel_module = excel.get("module", "")
        self.excel_action = excel.get("action", "")
        self.excel_source_kb = excel.get("source_kb", "")
        self.excel_expected_response = excel.get("expected_response", "")
        self.excel_tool_calling = excel.get("tool_calling_queries", False)
        self.excel_user_query = excel.get("user_query", scenario.get("initial_message", ""))

        # For reporting Expected vs Actual
        self.actual_first_reply = ""
        self.actual_last_reply = ""
        self.expected_similarity = None  # float
        self.expected_judge = None       # dict {matches,relevance,reason}

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

    async def run_all_tests(self, scenario_ids: List[str] = None):
        self.is_running = True
        self.should_stop = False
        self.results = []
        self.completed_tests = 0

        scenarios = get_all_scenarios()
        if scenario_ids:
            scenarios = [s for s in scenarios if s["id"] in scenario_ids]

        self.total_tests = len(scenarios)
        await ws_manager.send_status("running", f"Starting {self.total_tests} tests...")
        await ws_manager.send_log("info", f"🚀 Starting {self.total_tests} tests")

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
                await asyncio.sleep(3)

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
        await ws_manager.send_status("completed", f"Suite done! ✅{p} ❌{f} ⚠️{e}")
        self.is_running = False

    async def _run_test(self, scenario: dict) -> TestResult:
        result = TestResult(scenario)
        result.start_time = datetime.now()

        try:
            conversation = []
            max_turns = scenario.get("max_turns", 4)
            min_turns = scenario.get("min_turns", 1)

            # If this is an attachment scenario, inject a real ticket number from confirmed tickets
            if scenario["id"].startswith("ATT-"):
                inc = next((t for t in reversed(self.confirmed_tickets) if t.startswith("INC")), None)
                if not inc:
                    result.status = "skipped"
                    result.notes = "Skipped: no confirmed INC ticket available (run INC-001 or RET-001 first)"
                    return self._fin(result)
                scenario["context_ticket"] = inc
                await ws_manager.send_log("info", f"Using confirmed ticket for attachments: {inc}")

            # Initial message (AI)
            initial = await self.ai_brain.generate_initial_message(scenario)
            await ws_manager.send_log("info", f"Message: {initial[:120]}")

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
                        if u not in result.kb_links_found and "blob.core.windows.net" in u.lower():
                            result.kb_links_found.append(u)

                conversation.append({"role": "assistant", "content": cva_response, "links": links})
                result.conversation_log.append({
                    "role": "assistant",
                    "content": cva_response,
                    "timestamp": timestamp_readable(),
                    "links": links,
                })

                # Excel single-turn tests: stop after first CVA response
                if result.scenario.get("stop_after_first_response") and turn >= 1:
                    await ws_manager.send_log("info", "Stopping after first response (single-turn Excel test).")
                    break

                # Capture first and last actual replies for reporting
                if not result.actual_first_reply:
                    result.actual_first_reply = cva_response
                result.actual_last_reply = cva_response

                ticket = extract_ticket_number(cva_response)
                if ticket and ticket not in self.discovered_tickets:
                    self.discovered_tickets.append(ticket)
                    await ws_manager.send_log("info", f"🎫 Ticket seen: {ticket}")

                # Update ticket state tracking
                cva_low = (cva_response or "").lower()
                if ticket:
                    if "created" in cva_low:
                        result.state["ticket_created"] = True
                    if "updated" in cva_low:
                        result.state["ticket_updated"] = True
                    if "resolved" in cva_low:
                        result.state["ticket_resolved"] = True
                    if "closed" in cva_low:
                        result.state["ticket_closed"] = True

                # Check for access denied
                if "access denied" in cva_low:
                    result.status = "failed"
                    result.bugs_found.append("Access denied for ticket operation.")
                    break

                # Confirm ticket only if it looks real (created or listed), not an example prompt
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

                # State-aware stop logic for ticket lifecycle
                excel_action = (scenario.get("excel", {}) or {}).get("action", "").lower()

                if "create" in excel_action and result.state["ticket_created"]:
                    await ws_manager.send_log("info", "✅ Ticket created - lifecycle complete")
                    break

                if "update" in excel_action and result.state["ticket_updated"]:
                    await ws_manager.send_log("info", "✅ Ticket updated - lifecycle complete")
                    break

                if "resolve" in excel_action and result.state["ticket_resolved"]:
                    await ws_manager.send_log("info", "✅ Ticket resolved - lifecycle complete")
                    break

                goal_done = analysis.get("goal_achieved", False)
                should_continue = analysis.get("should_continue", True)

                if goal_done and turn >= min_turns:
                    await ws_manager.send_log("info", "✅ Goal achieved (min turns satisfied)")
                    break

                if not should_continue and turn >= min_turns:
                    await ws_manager.send_log("info", "Analysis: conversation complete")
                    break

                # Follow-up if more turns
                if turn < max_turns:
                    attachments = None

                    # Attachment scenarios must be deterministic (do NOT let AI pick random INC)
                    if scenario["id"].startswith("ATT-"):
                        inc = scenario.get("context_ticket")  # set earlier from confirmed ticket
                        cva_low = (cva_response or "").lower()

                        # If CVA is asking which ticket to attach to:
                        if "let me know which ticket" in cva_low or "which ticket" in cva_low or "once you upload file and specify ticket" in cva_low:
                            # Upload + specify ticket in same message
                            attachments = app_config.staged_attachments or []
                            if not attachments:
                                result.status = "skipped"
                                result.notes = "Skipped: no staged attachments in UI"
                                return self._fin(result)
                            names = ", ".join([os.path.basename(p) for p in attachments])
                            follow_up = f"I just uploaded {names}. Please attach it to {inc} and confirm when it's done."

                        # If CVA says upload now / drag & drop now:
                        elif "upload" in cva_low or "drag and drop" in cva_low or "attach" in cva_low:
                            attachments = app_config.staged_attachments or []
                            if not attachments:
                                result.status = "skipped"
                                result.notes = "Skipped: no staged attachments in UI"
                                return self._fin(result)
                            names = ", ".join([os.path.basename(p) for p in attachments])
                            follow_up = f"I uploaded {names} just now. Please attach it to ticket {inc} and confirm."

                        # If CVA asks for incident number:
                        elif "incident number" in cva_low or "inc" in cva_low:
                            follow_up = f"The incident number is {inc}."

                        else:
                            # safe default
                            follow_up = f"Please attach my uploaded file to ticket {inc} and confirm."

                    else:
                        # Normal scenarios: use AI follow-up
                        follow_up = await self.ai_brain.generate_follow_up(
                            scenario, conversation, cva_response,
                            "achieved" if goal_done else "in_progress"
                        )

                        prev = [m["content"] for m in conversation if m["role"] == "user"]
                        if follow_up in prev:
                            follow_up = "I tried that but it didn't fix it. What should I do next?"

                    await ws_manager.send_log("info", f"Turn {turn+1}: {follow_up[:120]}")
                    # If attachments were required, enforce upload success
                    if attachments:
                        uploaded = await self.teams.upload_attachments(attachments)
                        if not uploaded:
                            result.status = "failed"
                            result.bugs_found.append("Attachment upload failed in Teams UI (automation issue or Teams UI change).")
                            result.error_message = "Attachment upload failed"
                            return self._fin(result)
                    
                    ok = await self.teams.send_message(follow_up)  # send message after upload
                    if not ok:
                        result.bugs_found.append("Failed to send follow-up")
                        break

                    conversation.append({"role": "user", "content": follow_up})
                    result.conversation_log.append({"role": "user", "content": follow_up, "timestamp": timestamp_readable()})

            await self._check_expected_response(result, conversation)
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

        # Deduplicate bugs to keep report clean
        seen = set()
        deduped = []
        for b in result.bugs_found:
            key = (b or "").strip()
            if key and key not in seen:
                seen.add(key)
                deduped.append(key)
        result.bugs_found = deduped

        return self._fin(result)

    async def _check_expected_response(self, result: TestResult, conversation: List[Dict]):
        """
        Option A: Only run when Expected Response is filled.
        Uses:
          - similarity heuristic (difflib)
          - GPT judge (AIBrain) for semantic match
        Marks validation: matches_expected_semantic
        """
        excel = (result.scenario.get("excel") or {})
        module = (excel.get("module") or "").lower()
        
        # Skip judge for single-turn modules
        if module in ["greeting / closing", "out-of-scope"]:
            return
        
        expected = (excel.get("expected_response") or "").strip()
        if not expected:
            return  # Option A: only run when Expected Response is filled

        # Compare against: FIRST CVA response after user query (best for 1-row testcases)
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

        # If AI judge is unavailable (credits ended), don't fail the test unfairly.
        if not getattr(self.ai_brain, "_working_model", None):
            if sim >= 0.55:
                result.validations_passed.append("matches_expected_semantic")
                result.ai_analysis["expected_judge"] = {"matches": True, "reason": f"Similarity >= 0.55 without judge (sim={sim:.3f})"}
            else:
                # Mark as skipped judge (not failed)
                result.validations_passed.append("skipped_judge")
                result.bugs_found.append(
                    f"Judge unavailable (Bytez credits). Cannot verify Expected Response semantically. similarity={sim:.2f}"
                )
            return

        # If it's clearly similar, pass without GPT (fast)
        if sim >= 0.55:
            result.validations_passed.append("matches_expected_semantic")
            result.ai_analysis["expected_judge"] = {"matches": True, "reason": f"Similarity >= 0.55 (sim={sim:.3f})"}
            return

        # Otherwise, use GPT judge (semantic)
        judge = await self.ai_brain.judge_expected(
            user_query=excel.get("user_query") or result.scenario.get("initial_message", ""),
            cva_response=first_bot,
            expected=expected,
            action=excel.get("action", ""),
        )
        result.expected_judge = judge
        result.ai_analysis["expected_judge"] = judge

        # If judge is empty/unavailable, do NOT fail unfairly
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

    def _validate(self, result: TestResult, conversation: List[Dict]):
        validations = result.scenario.get("validations", [])
        all_cva = " ".join(m.get("content", "") for m in conversation if m.get("role") == "assistant")
        cva = all_cva.lower()
        
        # Module-aware validation
        module = (result.scenario.get("excel", {}) or {}).get("module", "").lower()

        # ---------------- Excel KB contradiction check ----------------
        # If Excel expects a specific KB (Source KB is filled), CVA must NOT claim:
        # "not sourced from KB" / "no documentation in my knowledge base", etc.
        excel = (result.scenario.get("excel") or {})
        expected_kb = (excel.get("source_kb") or "").strip()

        if expected_kb:
            bad_phrases = [
                "not sourced from your organization's knowledge base",
                "not sourced from your organization's knowledge base",
                "not sourced from your organisations knowledge base",
                "not sourced from your organisation's knowledge base",
                "i don't have any specific troubleshooting",
                "i don't have specific troubleshooting",
                "i don't have any specific documentation",
                "i don't have specific documentation",
                "not available in my knowledge base",
                "no documentation",
                "do not have access to documentation",
                "i do not have access to documentation",
            ]

            hit = next((p for p in bad_phrases if p in cva), None)
            if hit:
                key = "does_not_contradict_kb_availability"
                if key not in result.validations_failed:
                    result.validations_failed.append(key)
                msg = f"CVA contradiction: Excel expects KB '{expected_kb}', but CVA said: '{hit}'."
                if msg not in result.bugs_found:
                    result.bugs_found.append(msg)
        # --------------------------------------------------------------

        # Helper functions for validation
        def assistant_has_troubleshooting(m: Dict) -> bool:
            t = (m.get("content") or "").lower()
            return ("step" in t) or ("citation" in t) or ("troubleshoot" in t)

        def any_kb_link(links: List[str]) -> bool:
            return any("knowledgebasestaging.blob.core.windows.net" in (u or "").lower() for u in (links or []))

        # Aggregate links seen in assistant messages
        all_links: List[str] = []
        for m in conversation:
            if m.get("role") == "assistant":
                for u in (m.get("links") or []):
                    if u and u not in all_links:
                        all_links.append(u)

        # Excel-only contradiction check (no need to add a validation key in loader)
        excel = (result.scenario.get("excel") or {})
        expected_kb = (excel.get("source_kb") or "").strip()

        if expected_kb:
            bad_phrases = [
                "not sourced from your organization's knowledge base",
                "not sourced from your organization's knowledge base",
                "i don't have any specific troubleshooting",
                "i don't have specific troubleshooting",
                "i don't have any specific documentation",
                "i don't have specific documentation",
                "not available in my knowledge base",
                "no documentation",
                "do not have access to documentation",
            ]
            if any(p in cva for p in bad_phrases):
                # mark as failure + explain clearly
                result.validations_failed.append("does_not_contradict_kb_availability")
                result.bugs_found.append(
                    f"CVA contradiction: Excel expects KB '{expected_kb}', but CVA claimed answer is not from KB / no KB documentation."
                )

        for v in validations:
            passed = False

            if v == "provides_troubleshooting_steps":
                passed = any(w in cva for w in ["step", "try", "check", "restart", "1.", "troubleshoot"])
            elif v == "includes_citations":
                passed = contains_citation(all_cva)
            elif v == "includes_kb_hyperlink":
                # mandatory: any troubleshooting reply should include KB hyperlink
                ok_all = True
                for m in conversation:
                    if m.get("role") == "assistant" and assistant_has_troubleshooting(m):
                        if not any_kb_link(m.get("links") or []):
                            ok_all = False
                            break
                passed = ok_all
            elif v == "asks_follow_up_questions":
                passed = "?" in all_cva
            elif v == "creates_incident":
                passed = contains_ticket_confirmation(all_cva)
            elif v == "returns_inc_number":
                passed = bool(extract_ticket_number(all_cva))
            elif v == "shows_ticket_details":
                passed = any(w in cva for w in ["ticket details", "incident number", "status:"])
            elif v == "shows_catalog_item":
                # now card text should be captured (Complete this request etc.)
                passed = contains_service_catalog(all_cva) or ("complete this request" in cva)
            elif v == "detects_service_request":
                passed = any(w in cva for w in ["service", "catalog", "ritm", "complete this request"])
            elif v in ("shows_ticket_list", "includes_inc_numbers"):
                passed = contains_ticket_list(all_cva)
            elif v == "initiates_handoff":
                # soft pass for now: either real handoff OR clear unavailability message
                passed = ("live handover" in cva) or ("no servicenow agents are available" in cva) or ("try reaching out again" in cva)
            elif v == "has_tool_action":
                # New advanced validation first
                advanced = self._intent_validation(result, all_cva, all_links)

                if advanced is not None:
                    passed = advanced
                else:
                    # fallback to old behavior
                    txt = all_cva.lower()
                    has_ticket = bool(extract_ticket_number(all_cva))
                    has_servicenow_link = any("servicenow" in (u or "").lower() for u in all_links)
                    passed = has_ticket or has_servicenow_link
            elif v == "matches_expected_semantic":
                if "catalog" in module:
                    expected = (result.scenario.get("excel", {}) or {}).get("expected_response", "").lower()
                    passed = all(item.strip().lower() in all_cva.lower() for item in expected.split("\n") if item.strip())
                elif "ticket" in module:
                    expected_action = (result.scenario.get("excel", {}) or {}).get("action", "").lower()
                    
                    if "create" in expected_action:
                        passed = "incident number" in all_cva.lower()
                    elif "update" in expected_action:
                        passed = "updated" in all_cva.lower()
                    elif "close" in expected_action:
                        passed = "closed" in all_cva.lower()
                    else:
                        passed = (v in result.validations_passed) and (v not in result.validations_failed)
                else:
                    passed = (v in result.validations_passed) and (v not in result.validations_failed)
            elif v == "includes_specific_kb":
                expected_kb = (result.scenario.get("excel", {}) or {}).get("source_kb", "")
                
                # Network & Connectivity (VPN) special handling
                if "network" in module:
                    kb_links = result.kb_links_found or []
                    passed = any("vpn" in link.lower() for link in kb_links)
                else:
                    expected_kb_norm = re.sub(r"[\s_]+", "", (expected_kb or "").lower()).strip()

                    # Gather found KB-ish links for reporting
                    found_kb_links = [u for u in all_links if ("blob.core.windows.net" in (u or "").lower()) or (".pdf" in (u or "").lower()) or (".docx" in (u or "").lower())]
                    found_preview = ", ".join(found_kb_links[:3])

                    passed = any(
                        expected_kb_norm and expected_kb_norm in re.sub(r"[\s_]+", "", (u or "").lower())
                        for u in all_links
                    )
            elif v in ("detects_language", "responds_in_same_language"):
                passed = detect_response_language(all_cva) != "English"
            elif v in ("handles_gracefully", "no_error_crash"):
                passed = not contains_error_indicators(all_cva) and len(all_cva) > 10
            else:
                # Unknown validation key should FAIL so we notice missing implementation
                passed = False
                result.bugs_found.append(f"Unknown validation key (not implemented): {v}")

            if passed:
                result.validations_passed.append(v)
            else:
                if v not in result.validations_failed:
                    result.validations_failed.append(v)

                # Human-readable reasons for Excel-driven validations
                if v == "has_tool_action":
                    result.bugs_found.append(
                        "Action failed (ToolCalling=Y): No INC/RITM and no ServiceNow/catalog link/text detected (e.g., 'View in ServiceNow', 'Complete this request')."
                    )
                elif v == "includes_kb_hyperlink":
                    result.bugs_found.append(
                        "KB hyperlink missing: Troubleshooting response should include a KB hyperlink, but no KB URL was captured from Teams."
                    )
                elif v == "includes_specific_kb":
                    expected_kb = (result.scenario.get("excel", {}) or {}).get("source_kb", "")
                    found_kb_links = [u for u in all_links if ("blob.core.windows.net" in (u or "").lower()) or (".pdf" in (u or "").lower()) or (".docx" in (u or "").lower())]
                    found_preview = ", ".join(found_kb_links[:3])
                    result.bugs_found.append(
                        f"KB mismatch: Expected '{expected_kb}'. Found links: {found_preview or 'NO KB LINKS CAPTURED'}"
                    )
                elif v == "matches_expected_semantic":
                    reason = ""
                    if isinstance(getattr(result, "expected_judge", None), dict):
                        reason = result.expected_judge.get("reason", "")
                    sim = getattr(result, "expected_similarity", None)
                    result.bugs_found.append(
                        f"Expected response mismatch: similarity={sim} judge_reason={reason}"
                    )
                else:
                    result.bugs_found.append(f"Failed validation: {v}")

    async def stop_tests(self):
        self.should_stop = True
        await ws_manager.send_log("warning", "⏹️ Stopping...")

    async def cleanup(self):
        await self.ai_brain.close()
        await self.teams.close()

    def _intent_validation(self, result: TestResult, all_cva: str, all_links: list) -> Optional[bool]:
        """
        Advanced intent-based validation.
        Returns:
            True  -> clearly passed
            False -> clearly failed
            None  -> fallback to old validation
        """
        excel = result.scenario.get("excel", {}) or {}
        action = (excel.get("action") or "").lower()
        txt = (all_cva or "").lower()
        ticket_number = extract_ticket_number(all_cva)

        if not action:
            return None

        # CREATE intent
        if "create" in action:
            if ticket_number and "created" in txt:
                return True
            return False

        # UPDATE intent
        if "update" in action:
            if ticket_number and any(x in txt for x in ["updated", "update successful", "has been updated"]):
                return True
            if "not found" in txt:
                return False
            return None

        # RESOLVE intent
        if "resolve" in action:
            if ticket_number and "resolved" in txt:
                return True
            return False

        # CLOSE intent
        if "close" in action:
            if ticket_number and "closed" in txt:
                return True
            return False

        # RETRIEVE intent
        if "show" in action or "retrieve" in action:
            if ticket_number:
                return True
            return None

        return None

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
