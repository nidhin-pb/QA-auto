"""
AI Brain v8
Fixes:
- AI follow-up no longer mimics bot tone (stronger system prompt + response filtering)
- Better template follow-ups that are context-aware
- Single-turn scenarios never get follow-ups
"""
import asyncio
import re
import json
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from config import app_config
from websocket_manager import ws_manager

_executor = ThreadPoolExecutor(max_workers=2)


# Phrases that indicate the AI is acting as the BOT instead of the USER
BOT_TONE_PHRASES = [
    "i can only assist with",
    "i'm here to help",
    "i'm happy to help",
    "how can i assist",
    "how can i help",
    "please let me know",
    "is there anything else",
    "i don't have the authority",
    "i'm not able to",
    "that information is outside",
    "i appreciate your request, but",
    "i can help you with",
    "i'm designed to help",
    "if you have any it or servicenow",
    "if you need help with it support",
    "you should contact the finance",
    "that's outside my scope",
    "i'm only able to assist",
]


def _sounds_like_bot(text: str) -> bool:
    """Detect if generated text sounds like a bot/assistant instead of a user/employee."""
    t = (text or "").lower()
    return any(phrase in t for phrase in BOT_TONE_PHRASES)


class AIBrain:
    def __init__(self):
        self.bytez_keys = [
            getattr(app_config.ai, "bytez_api_key", ""),
            getattr(app_config.ai, "bytez_api_key_2", ""),
        ]
        self.bytez_keys = [k for k in self.bytez_keys if k]

        self._api_tested = False
        self._working_model: Optional[str] = None
        self._ai_disabled = False
        self.ai_available = True

        self.bytez_timeout_seconds = 40
        self._bytez_sem = asyncio.Semaphore(1)

        self.models_to_try = [
            "openai/gpt-4o",
            "openai/gpt-oss-20b",
            "inference-net/Schematron-3B",
            "google/gemma-3-1b-it",
            "Qwen/Qwen3-0.6B",
        ]

    def is_available(self):
        return not self._ai_disabled and self._working_model is not None

    async def _test_apis(self):
        if self._api_tested:
            return
        self._api_tested = True

        if not self.bytez_keys:
            self._ai_disabled = True
            self.ai_available = False
            self._working_model = None
            await ws_manager.send_log("warning", "⚠️ No BYTEZ_API_KEY configured. Using templates only.")
            return

        await ws_manager.send_log("info", f"Bytez keys configured: {len(self.bytez_keys)}")

        for model_name in self.models_to_try:
            await ws_manager.send_log("info", f"Testing {model_name}...")

            probe = await self._call_bytez_single_model(
                model_name=model_name,
                prompt="Reply with exactly: WORKING",
                system="Reply with exactly one word: WORKING"
            )

            if probe and probe.strip().upper() == "WORKING":
                self._working_model = model_name
                self.ai_available = True
                await ws_manager.send_log("info", f"✅ Selected model: {model_name}")
                return

            await ws_manager.send_log("warning", f"{model_name} probe not valid (got: {(probe or '')[:60]})")

        self._working_model = None
        self._ai_disabled = True
        self.ai_available = False
        await ws_manager.send_log("warning", "⚠️ No AI model available (credits/network). Using templates only.")

    async def _call_bytez_single_model(self, model_name: str, prompt: str, system: str = None) -> str:
        if self._ai_disabled:
            return ""

        def _run_with_key(key: str):
            try:
                from bytez import Bytez
                sdk = Bytez(key)
                model = sdk.model(model_name)

                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                results = model.run(messages)
                if results.error:
                    return f"__ERROR__: {results.error}"

                out = results.output
                if out is None:
                    return ""

                if isinstance(out, str):
                    return out.strip()

                if isinstance(out, list) and out:
                    for item in reversed(out):
                        if isinstance(item, dict):
                            if item.get("role") == "assistant":
                                return str(item.get("content", "")).strip()
                            for k in ("content", "generated_text", "text"):
                                if k in item:
                                    return str(item[k]).strip()
                    return str(out[-1]).strip()

                if isinstance(out, dict):
                    for k in ("content", "generated_text", "text", "message", "response"):
                        if k in out:
                            return str(out[k]).strip()
                    return str(out).strip()

                return str(out).strip()

            except Exception as e:
                return f"__ERROR__: {str(e)}"

        async with self._bytez_sem:
            for i, key in enumerate(self.bytez_keys):
                loop = asyncio.get_running_loop()
                try:
                    result = await asyncio.wait_for(
                        loop.run_in_executor(_executor, _run_with_key, key),
                        timeout=self.bytez_timeout_seconds
                    )
                except asyncio.TimeoutError:
                    await ws_manager.send_log("warning", f"Bytez timeout ({model_name}) on key {i+1}")
                    continue

                if not result:
                    continue

                if result.startswith("__ERROR__:"):
                    msg = result[10:].strip()
                    low = msg.lower()

                    if any(x in low for x in ["min balance", "credits", "unauthorized", "could not find route", "rate limited"]):
                        await ws_manager.send_log("warning", f"Bytez key {i+1} failed ({model_name}): {msg[:160]}")
                        continue

                    await ws_manager.send_log("warning", f"Bytez error ({model_name}): {msg[:160]}")
                    return ""

                return self._clean_response(result)

        return ""

    async def _call_bytez_any_model(self, prompt: str, system: str = None, prefer_model: str = None) -> str:
        await self._test_apis()
        if self._ai_disabled:
            return ""

        candidates = []
        if prefer_model:
            candidates.append(prefer_model)
        for m in self.models_to_try:
            if m not in candidates:
                candidates.append(m)

        for m in candidates:
            txt = await self._call_bytez_single_model(m, prompt, system=system)
            if txt:
                self._working_model = m
                return txt
        return ""

    def _clean_response(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"<s>.*?</s>", "", text, flags=re.DOTALL)
        text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)

        for prefix in ["Assistant:", "Employee:", "User:", "Reply:", "Response:", "Answer:", "Message:", "Bot:", "Human:"]:
            if text.strip().startswith(prefix):
                text = text.strip()[len(prefix):]

        return text.strip().strip('"\'').strip()

    def _model_ok_for_initial_rewrite(self) -> bool:
        return bool(self._working_model) and self._working_model.startswith("openai/")

    async def generate_initial_message(self, scenario: dict) -> str:
        await self._test_apis()
        hint = scenario.get("initial_message", "") or ""

        if self._model_ok_for_initial_rewrite() and hint and scenario.get("min_turns", 1) > 1:
            system = (
                "Rewrite the message with the same meaning. "
                "Return ONLY the rewritten message. Under 50 words."
            )
            prompt = f"Rewrite with same meaning:\n{hint}"
            txt = await self._call_bytez_any_model(prompt, system=system, prefer_model=self._working_model)
            if txt and 5 < len(txt) < 200 and not _sounds_like_bot(txt):
                await ws_manager.send_log("info", f"🤖 AI initial: {txt[:80]}")
                return txt

        return hint

    async def generate_follow_up(self, scenario: dict, history: List[Dict], cva_response: str, goal_status: str) -> str:
        await self._test_apis()

        # Safe follow-up fallback when AI unavailable
        if not self.is_available():
            await ws_manager.send_log("warning", "AI unavailable — using template follow-up")
            return self._template_follow_up(scenario, history, cva_response)

        # If LLM available AND model is strong enough, try LLM follow-up
        if not self._ai_disabled and self._working_model:
            txt = await self._ai_follow_up(scenario, history, cva_response)
            if txt and not _sounds_like_bot(txt):
                prev = [m["content"] for m in history if m["role"] == "user"]
                if txt not in prev:
                    await ws_manager.send_log("info", f"🤖 AI follow-up: {txt[:80]}")
                    return txt
                else:
                    await ws_manager.send_log("warning", "AI follow-up was duplicate, using template")
            elif txt:
                await ws_manager.send_log("warning", f"AI follow-up sounded like bot, using template instead: {txt[:60]}")

        return self._template_follow_up(scenario, history, cva_response)

    async def _ai_follow_up(self, scenario: dict, history: List[Dict], cva_response: str) -> str:
        conv_lines = []
        for msg in history[-8:]:
            role = "Employee" if msg["role"] == "user" else "IT Bot"
            limit = 500 if msg["role"] == "user" else 1400
            conv_lines.append(f"{role}: {msg['content'][:limit]}")
        conv_text = "\n".join(conv_lines)

        system = (
            "You are an EMPLOYEE (end user) chatting with an IT helpdesk chatbot.\n"
            "You are NOT the bot. You are the person asking for help.\n"
            "NEVER say things like 'I can help you', 'How can I assist', 'I'm here to help', "
            "'please let me know', 'If you need help with IT'.\n"
            "NEVER give advice or redirect the user. YOU ARE the user.\n"
            "Answer the bot's questions about YOUR problem. Describe YOUR issue.\n"
            "Provide details like error messages, what you tried, your device info.\n"
            "Do not change topic. Do not repeat previous messages.\n"
            "Return ONLY your reply as the employee. Under 60 words."
        )
        bot_window = (cva_response or "")[:2500]
        prompt = (
            f"CONVERSATION SO FAR:\n{conv_text}\n\n"
            f"THE IT BOT JUST SAID:\n\"{bot_window}\"\n\n"
            f"YOUR GOAL AS EMPLOYEE: {scenario.get('goal','Get help')}\n\n"
            f"Write your reply AS THE EMPLOYEE (not the bot). "
            f"Answer the bot's questions about your problem:"
        )

        return await self._call_bytez_any_model(prompt, system=system, prefer_model=self._working_model)

    async def analyze_response(self, scenario: dict, cva_response: str, history: List[Dict]) -> dict:
        cva = (cva_response or "").lower()
        goal = (scenario.get("goal", "") or "").lower()

        has_error = any(w in cva for w in ["sorry, i can't", "error occurred", "something went wrong"])
        has_steps = any(w in cva for w in ["step", "try", "1.", "first", "check", "go to"])
        has_ticket = any(w in cva for w in ["inc00", "ritm00", "incident number", "ticket has been"])
        has_catalog = any(w in cva for w in ["catalog", "complete this request"])

        goal_achieved = False
        if "troubleshoot" in goal and has_steps:
            goal_achieved = True
        if "create" in goal and has_ticket:
            goal_achieved = True
        if "catalog" in goal and has_catalog:
            goal_achieved = True

        should_continue = (not goal_achieved) and (not has_error) and (len(history) < 12)
        if "?" in (cva_response or "") and not goal_achieved:
            should_continue = True

        return {
            "goal_achieved": goal_achieved,
            "should_continue": should_continue,
            "has_error": has_error,
            "notes": f"Model: {self._working_model or 'templates'}",
        }

    def _template_follow_up(self, scenario: dict, history: List[Dict], cva_response: str) -> str:
        """Context-aware template follow-ups that sound like a real employee."""
        cva = (cva_response or "").lower()
        goal = (scenario.get("goal", "") or "").lower()
        turn = len([m for m in history if m["role"] == "user"])

        # Smarter AI follow-up guard
        if "no active incident ticket found" in cva:
            return "Okay, can you show me my open tickets so I can confirm the correct ticket number?"

        # Special handling: ticket created
        if "incident ticket created" in cva or "incident number" in cva:
            return "Thank you. Can you confirm the status and expected resolution time?"

        # If CVA asks a question, give a realistic employee answer
        if "?" in (cva_response or ""):
            # Detect what CVA is asking about
            if any(w in cva for w in ["error message", "exact error", "what error"]):
                return "The error message says 'Connection timed out - unable to reach server'. It started happening yesterday."
            if any(w in cva for w in ["device", "laptop", "computer", "model"]):
                return "I'm using a Dell Latitude 5520 running Windows 11. It's about 2 years old."
            if any(w in cva for w in ["tried", "attempted", "troubleshoot", "steps"]):
                return "Yes, I've already tried restarting my computer and clearing the cache, but the issue persists."
            if any(w in cva for w in ["others", "anyone else", "team", "colleagues"]):
                return "No, it seems to be only affecting my machine. My colleagues are not having this issue."
            if any(w in cva for w in ["when", "how long", "started", "since"]):
                return "It started about 2 days ago, on Monday morning after the weekend."
            if any(w in cva for w in ["urgency", "urgent", "impact", "priority"]):
                return "It's fairly urgent as it's blocking my daily work. I'd say medium to high priority."
            if any(w in cva for w in ["software", "application", "app", "which"]):
                return "It's happening with Microsoft Outlook and also when I try to access SharePoint in the browser."
            # Generic question response
            return "Yes, I tried that already but the issue is still happening. What else can I try?"

        # If CVA provides troubleshooting steps and goal involves ticket creation
        if "ticket" in goal and turn >= 2:
            return "I've tried all those steps but nothing worked. Can you please create a ticket for this issue?"

        # Progressive responses for troubleshooting
        if turn <= 1:
            return "I tried that but the issue is still there. What else can I try?"
        if turn == 2:
            return "Still not working after trying those steps. This is really affecting my work. What's the next step?"
        if turn == 3:
            return "Nothing has worked so far. Can you please create a ticket so the IT team can look into this?"
        return "Thank you for your help."

    async def judge_expected(self, user_query: str, cva_response: str, expected: str, action: str = "") -> dict:
        await self._test_apis()
        if not self.is_available():
            return {"matches": False, "relevance": 0, "reason": "AI unavailable — skipped"}
        if self._ai_disabled:
            return {"matches": False, "relevance": 0, "reason": "Judge unavailable (no working model)."}

        system = (
            "You are a QA evaluator. Accept paraphrases. Do not require exact wording. "
            "Return ONLY valid JSON."
        )
        prompt = f"""
USER QUERY:
{user_query}

EXPECTED RESPONSE (intent-level):
{expected}

BOT RESPONSE:
{cva_response}

ACTION CONTEXT:
{action}

Return JSON:
{{"matches": true/false, "relevance": 0-10, "reason": "short"}}
"""
        txt = await self._call_bytez_any_model(prompt, system=system, prefer_model=self._working_model)
        if not txt:
            return {"matches": False, "relevance": 0, "reason": "Judge returned empty response."}

        m = re.search(r"\{.*\}", txt, flags=re.DOTALL)
        if not m:
            return {"matches": False, "relevance": 0, "reason": f"Judge non-JSON output: {txt[:200]}"}

        try:
            data = json.loads(m.group(0))
            return {
                "matches": bool(data.get("matches", False)),
                "relevance": int(data.get("relevance", 0)),
                "reason": str(data.get("reason", ""))[:600],
            }
        except Exception as e:
            return {"matches": False, "relevance": 0, "reason": f"Judge JSON parse error: {e}"}

    async def judge_action(self, user_query: str, cva_response: str, action: str, links: list, source_kb: str = "", tool_calling: bool = False) -> dict:
        await self._test_apis()
        if not self.is_available():
            return {
                "passed": False, 
                "score": 0, 
                "reason": "AI unavailable — skipped", 
                "detected": {}
            }
        if self._ai_disabled:
            return {"passed": False, "score": 0, "reason": "Judge unavailable (no working model).", "detected": {}}

        system = (
            "You are a strict QA evaluator for an IT/ServiceNow chatbot. "
            "Return ONLY valid JSON."
        )
        prompt = f"""
USER QUERY:
{user_query}

REQUIRED ACTION:
{action}

SOURCE KB:
{source_kb}

TOOL CALLING REQUIRED:
{"Y" if tool_calling else "N"}

BOT RESPONSE:
{cva_response}

CAPTURED LINKS:
{links}

Return JSON:
{{"passed": true/false, "score": 0-10, "reason": "short", "detected": {{}}}}
"""
        txt = await self._call_bytez_any_model(prompt, system=system, prefer_model=self._working_model)
        if not txt:
            return {"passed": False, "score": 0, "reason": "Judge returned empty response.", "detected": {}}

        m = re.search(r"\{.*\}", txt, flags=re.DOTALL)
        if not m:
            return {"passed": False, "score": 0, "reason": f"Judge non-JSON output: {txt[:200]}", "detected": {}}

        try:
            return json.loads(m.group(0))
        except Exception:
            return {"passed": False, "score": 0, "reason": f"Judge JSON parse error: {txt[:200]}", "detected": {}}

    async def close(self):
        pass
