"""
Teams Browser Automation v6
Fixes:
- Robust adaptive card + rich message capture (prevents SR-001/RET-001 timeouts)
- Extract href hyperlinks from Teams DOM (for mandatory KB hyperlink validation)
- Improved timeout screenshots (auto-scroll to bottom)
- Optional attachment upload support (used by attachment scenarios)
"""
import os
import sys
import asyncio
import base64
import re
import hashlib
from typing import Optional, List, Dict, Set, Tuple
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from config import app_config
from utils import ensure_dir, timestamp, sanitize_filename
from websocket_manager import ws_manager


LOADING_PHRASES = [
    "processing your request", "please hold on", "⏳",
    "typing", "please wait", "one moment", "working on it",
]

CARD_BUTTON_TEXT = [
    "complete this request",
    "view details",
    "view in servicenow",
    "start chat handover",
]

CARD_TEXT_INDICATORS = [
    "card - access it on",
    "go.skype.com/cards.unsupported",
    "complete this request",
    "view details",
    "view in servicenow",
]


def make_hash(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())[:500]
    return hashlib.md5(cleaned.encode("utf-8", errors="ignore")).hexdigest()[:16]


def is_loading(text: str) -> bool:
    t = (text or "").lower().strip()
    if len(t) < 60:
        for p in LOADING_PHRASES:
            if p in t:
                return True
    if len(t) <= 5:
        return True
    return False


def looks_like_card(text: str) -> bool:
    t = (text or "").lower()
    return any(ind in t for ind in CARD_TEXT_INDICATORS)


def deduplicate(text: str) -> str:
    paragraphs = re.split(r"\n{2,}", text or "")
    seen = set()
    unique = []
    for p in paragraphs:
        key = re.sub(r"\s+", " ", p.strip())
        if key and key not in seen and len(key) > 3:
            seen.add(key)
            unique.append(p.strip())
    return "\n\n".join(unique)


class TeamsAutomator:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.is_logged_in = False
        self.is_cva_open = False

        self._seen_hashes: Set[str] = set()
        self._last_sent: str = ""

        # NEW: last response links extracted from DOM <a href="...">
        self.last_response_links: List[str] = []

        ensure_dir(app_config.screenshot_dir)

    async def initialize(self):
        await ws_manager.send_log("info", "Initializing browser...")
        self.playwright = await async_playwright().start()
        for ch, nm in [("chrome", "Chrome"), ("msedge", "Edge"), (None, "Chromium")]:
            try:
                args = ['--disable-blink-features=AutomationControlled']
                if sys.platform == 'linux': args.append('--no-sandbox')
                kw = {"headless": app_config.headless, "slow_mo": app_config.browser_slow_mo, "args": args}
                if ch: kw["channel"] = ch
                self.browser = await self.playwright.chromium.launch(**kw)
                await ws_manager.send_log("info", f"Launched {nm}")
                break
            except Exception:
                continue
        else:
            try:
                self.browser = await self.playwright.firefox.launch(headless=app_config.headless, slow_mo=app_config.browser_slow_mo)
            except Exception:
                raise RuntimeError("No browser")
        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
            ignore_https_errors=True,
            device_scale_factor=1,
        )
        self.context.set_default_timeout(30000)
        self.page = await self.context.new_page()

        # Reduce noisy crashes from console/page errors
        self.page.on("pageerror", lambda _: None)
        self.page.on("console", lambda _: None)

    async def login(self, email: str, password: str) -> bool:
        try:
            await self.page.goto(app_config.teams.teams_url, wait_until="load", timeout=60000)
            await asyncio.sleep(5)
            if not any(d in self.page.url for d in ["login.microsoftonline.com", "login.live.com"]):
                try:
                    await self.page.locator('a:has-text("Sign in"), button:has-text("Sign in")').first.click(timeout=10000)
                    await asyncio.sleep(5)
                except Exception: pass
            await self._login_flow(email, password)
            if await self._wait_teams():
                self.is_logged_in = True
                await ws_manager.send_log("info", "✅ Logged in!")
                return True
            return False
        except Exception as e:
            await ws_manager.send_log("error", f"Login failed: {str(e)}")
            return False

    async def _login_flow(self, email, password):
        await asyncio.sleep(2)
        for _ in range(8):
            for s in ['input[name="loginfmt"]', '#i0116', 'input[type="email"]']:
                try:
                    inp = self.page.locator(s).first
                    if await inp.is_visible(timeout=2000):
                        await inp.fill(email)
                        if await inp.input_value(): await self._submit(); await asyncio.sleep(4); break
                except Exception: continue
            else: await asyncio.sleep(2); continue
            break
        for _ in range(8):
            for s in ['input[name="passwd"]', '#i0118', 'input[type="password"]']:
                try:
                    inp = self.page.locator(s).first
                    if await inp.is_visible(timeout=2000):
                        await inp.fill(password)
                        if await inp.input_value(): await self._submit(); await asyncio.sleep(5); break
                except Exception: continue
            else: await asyncio.sleep(2); continue
            break
        await asyncio.sleep(3)
        for _ in range(5):
            for s in ['#idSIButton9', 'input[value="Yes"]', 'button:has-text("Yes")', 'button:has-text("Accept")', 'button:has-text("Continue")']:
                try:
                    btn = self.page.locator(s).first
                    if await btn.is_visible(timeout=2000): await btn.click(); await asyncio.sleep(3); break
                except Exception: continue
            if "teams.microsoft.com" in self.page.url: break

    async def _submit(self):
        for s in ['#idSIButton9', 'input[type="submit"]']:
            try:
                if await self.page.locator(s).first.is_visible(timeout=2000):
                    await self.page.locator(s).first.click(); return
            except Exception: continue
        await self.page.keyboard.press("Enter")

    async def _wait_teams(self):
        """
        Wait until Teams main UI is likely ready.
        IMPORTANT: Do NOT hard-fail if we can't detect nav reliably,
        because Teams DOM changes often. We'll continue with a warning.
        """
        await asyncio.sleep(3)
        await self._dismiss()

        selectors = [
            # Old + new variants (Teams changes frequently)
            'button[aria-label*="Chat"]',
            '#app-bar-chat-button',
            '[data-tid="app-bar-chat-button"]',
            'button[data-tid="app-bar-chat-button"]',
            'nav[role="navigation"]',
            'div[role="navigation"]',
            '[data-tid="app-bar"]',
        ]

        for i in range(60):
            await asyncio.sleep(2)

            # Must be on teams domain
            if "teams.microsoft.com" not in (self.page.url or ""):
                continue

            if i % 5 == 0:
                await self._dismiss()

            for s in selectors:
                try:
                    loc = self.page.locator(s).first
                    if await loc.is_visible(timeout=1500):
                        await self._dismiss()
                        return True
                except Exception:
                    continue

        # Don't block execution; just warn + capture evidence
        await ws_manager.send_log(
            "warning",
            f"Teams UI not fully detected after wait. Continuing anyway. Current URL: {self.page.url}"
        )
        await self._take_screenshot(f"teams_ui_not_detected_{timestamp()}")
        return True

    async def _dismiss(self):
        for s in ['button:has-text("Use the web app instead")', 'button:has-text("Continue")', 'button:has-text("Got it")', 'button:has-text("OK")', 'button:has-text("Dismiss")', 'button:has-text("Skip")', 'button:has-text("Maybe later")', 'button[aria-label="Close"]']:
            try:
                btn = self.page.locator(s).first
                if await btn.is_visible(timeout=600): await btn.click(); await asyncio.sleep(0.5)
            except Exception: continue

    async def open_cva_chat(self) -> bool:
        cva = app_config.teams.cva_app_name; await asyncio.sleep(2)
        try:
            for s in ['button[aria-label="Chat"]', '#app-bar-chat-button']:
                try:
                    if await self.page.locator(s).first.is_visible(timeout=3000):
                        await self.page.locator(s).first.click(); await asyncio.sleep(3); break
                except Exception: continue
            for t in [cva, "IT Servicedesk", "Servicedesk", "Service desk"]:
                try:
                    item = self.page.locator(f'span:has-text("{t}")').first
                    if await item.is_visible(timeout=3000):
                        await item.click()
                        await asyncio.sleep(3)
                        self.is_cva_open = True
                        await self.reset_chat_context()
                        await ws_manager.send_log("info", f"✅ Opened CVA chat: {t}")
                        return True
                except Exception:
                    continue
        except Exception: pass
        return False

    # ------------------- Chat capture (NEW) -------------------

    async def _scroll_to_bottom(self):
        try:
            await self.page.evaluate(
                """() => {
                    const candidates = [
                      document.querySelector('div[class*="chat-body"]'),
                      document.querySelector('div[role="main"]'),
                      document.scrollingElement,
                      document.body
                    ].filter(Boolean);
                    for (const el of candidates) {
                      try { el.scrollTop = el.scrollHeight; } catch(e) {}
                    }
                }"""
            )
        except Exception:
            pass

    async def _collect_listitems_rich(self) -> List[Dict]:
        """
        Returns list of {text, links, buttons}.
        Uses a single evaluate() for speed + reliability.
        """
        try:
            items = await self.page.evaluate(
                """() => {
                    const nodes = Array.from(document.querySelectorAll('div[role="listitem"]'));
                    return nodes.map(n => {
                        const text = (n.innerText || '').trim();
                        const links = Array.from(n.querySelectorAll('a[href]'))
                          .map(a => a.href)
                          .filter(Boolean);
                        const buttons = Array.from(n.querySelectorAll('button'))
                          .map(b => (b.innerText || '').trim())
                          .filter(Boolean);
                        return { text, links, buttons };
                    });
                }"""
            )
            if not isinstance(items, list):
                return []
            # Filter out empties
            cleaned = []
            for it in items:
                text = (it.get("text") or "").strip()
                links = it.get("links") or []
                buttons = it.get("buttons") or []
                if text or links or buttons:
                    cleaned.append({"text": text, "links": links, "buttons": buttons})
            return cleaned
        except Exception:
            return []

    async def reset_chat_context(self):
        await asyncio.sleep(1)
        await self._scroll_to_bottom()
        items = await self._collect_listitems_rich()
        for it in items[-40:]:
            h = make_hash(it.get("text", "") + " ".join(it.get("links", [])) + " ".join(it.get("buttons", [])))
            self._seen_hashes.add(h)
        self._last_sent = ""
        self.last_response_links = []
        await ws_manager.send_log("info", f"Reset: {len(self._seen_hashes)} hashes tracked")

    # ------------------- Sending -------------------

    async def send_message(self, message: str, attachments: Optional[List[str]] = None) -> bool:
        try:
            self._last_sent = message

            await self._scroll_to_bottom()

            # mark current as seen
            items = await self._collect_listitems_rich()
            for it in items[-40:]:
                h = make_hash(it.get("text", "") + " ".join(it.get("links", [])) + " ".join(it.get("buttons", [])))
                self._seen_hashes.add(h)

            inp = await self._find_input()
            if not inp:
                await ws_manager.send_log("error", "No input box!")
                return False

            await inp.click()
            await asyncio.sleep(0.2)

            mod = "Meta" if sys.platform == "darwin" else "Control"
            await self.page.keyboard.press(f"{mod}+a")
            await asyncio.sleep(0.05)
            await self.page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)

            # If attachments are requested, upload before typing/sending
            if attachments:
                ok = await self.upload_attachments(attachments)
                if not ok:
                    await ws_manager.send_log("warning", "Attachment upload failed; continuing without attachment.")

            await self.page.keyboard.type(message, delay=25)
            await asyncio.sleep(0.4)

            await self._take_screenshot(f"msg_typed_{timestamp()}")

            # Send
            for s in ['button[aria-label="Send"]', 'button[data-tid="send-button"]']:
                try:
                    btn = self.page.locator(s).first
                    if await btn.is_visible(timeout=1500) and await btn.is_enabled(timeout=1000):
                        await btn.click()
                        break
                except Exception:
                    continue
            else:
                await self.page.keyboard.press("Enter")

            await asyncio.sleep(1.5)
            await ws_manager.send_log("info", "✉️ Message sent!")
            await ws_manager.send_chat_message("user", message)
            return True
        except Exception as e:
            await ws_manager.send_log("error", f"Send failed: {str(e)}")
            return False

    async def _find_input(self):
        for s in [
            'div[role="textbox"][aria-label*="Type a message"]',
            'div[data-tid="ckeditor"]',
            'div[role="textbox"]',
            'div[contenteditable="true"]',
        ]:
            try:
                el = self.page.locator(s).first
                if await el.is_visible(timeout=2000):
                    return el
            except Exception:
                continue
        return None

    # ------------------- Attachments (used in Part 2) -------------------

    async def upload_attachments(self, paths: List[str]) -> bool:
        """
        Best-effort upload in Teams web:
        - Try set_input_files on any input[type=file]
        - If not found, try clicking Attach and using file chooser
        """
        paths = [p for p in (paths or []) if p and os.path.exists(p)]
        if not paths:
            return False

        await ws_manager.send_log("info", f"📎 Uploading {len(paths)} attachment(s)...")
        await self._scroll_to_bottom()

        # Attempt 1: direct input[type=file]
        try:
            inputs = self.page.locator('input[type="file"]')
            count = await inputs.count()
            if count > 0:
                # pick last input (often the compose upload input)
                await inputs.nth(count - 1).set_input_files(paths)
                await asyncio.sleep(2)
                return True
        except Exception:
            pass

        # Attempt 2: click attach + expect chooser
        attach_selectors = [
            'button[aria-label*="Attach"]',
            'button[title*="Attach"]',
            'button:has(i[class*="paperclip"])',
            'button:has-text("Attach")',
        ]
        for sel in attach_selectors:
            try:
                btn = self.page.locator(sel).first
                if await btn.is_visible(timeout=1500):
                    async with self.page.expect_file_chooser(timeout=5000) as fc_info:
                        await btn.click()
                    fc = await fc_info.value
                    await fc.set_files(paths)
                    await asyncio.sleep(2)
                    return True
            except Exception:
                continue

        return False

    # ------------------- Waiting for response (CRITICAL FIX) -------------------

    async def wait_for_response(self, timeout: int = None) -> Optional[str]:
        """
        Robust response wait:
        - Once any new CVA content appears, we wait for a short "quiet period"
          and then return the last captured content.
        - Prevents timeouts when cards appear only once (RET-001 issue).
        - Captures hyperlinks from DOM <a href="..."> into self.last_response_links.
        """
        timeout = timeout or app_config.max_wait_for_response
        await ws_manager.send_log("info", f"Waiting for CVA response ({timeout}s)...")

        elapsed = 0.0
        interval = float(app_config.message_check_interval)
        found_loading = False

        last_combined: str = ""
        last_links: List[str] = []
        quiet_polls = 0
        quiet_required = 3

        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval

            await self._scroll_to_bottom()
            items = await self._collect_listitems_rich()
            recent = items[-25:] if items else []

            new_texts: List[str] = []
            new_links: List[str] = []
            saw_card = False

            for it in recent:
                text = (it.get("text") or "").strip()
                links = it.get("links") or []
                buttons = it.get("buttons") or []

                combined_for_hash = text + " " + " ".join(links) + " " + " ".join(buttons)
                h = make_hash(combined_for_hash)
                if h in self._seen_hashes:
                    continue

                # loading
                if text and is_loading(text):
                    if not found_loading:
                        found_loading = True
                        await ws_manager.send_log("info", "CVA is processing... ⏳")
                        # extend patience slightly
                        timeout = max(timeout, int(elapsed + 60))
                    self._seen_hashes.add(h)
                    continue

                # skip our own echo
                if self._is_own(text):
                    self._seen_hashes.add(h)
                    continue

                # Card detection
                if looks_like_card(text) or any(b.lower() in CARD_BUTTON_TEXT for b in buttons):
                    saw_card = True

                # Accept as content even if empty text but has buttons/links
                payload_text = text.strip()
                if not payload_text and (buttons or links):
                    payload_text = " ".join(buttons).strip() or "[Rich content]"
                if payload_text:
                    new_texts.append(payload_text)

                for u in links:
                    if u and u not in new_links:
                        new_links.append(u)

                # Mark seen
                self._seen_hashes.add(h)

            if new_texts:
                combined = deduplicate("\n\n".join(new_texts)).strip()
                if combined:
                    last_combined = combined
                    last_links = new_links
                    quiet_polls = 0
                    quiet_required = 1 if saw_card else 3
                    continue

            # If we previously captured something, return after quiet period
            if last_combined:
                quiet_polls += 1
                if quiet_polls >= quiet_required:
                    self.last_response_links = last_links
                    await ws_manager.send_log("info", f"CVA responded ({len(last_combined)} chars, links={len(last_links)})")
                    await ws_manager.send_chat_message("cva", last_combined[:2000])
                    await self._take_screenshot(f"response_{timestamp()}")
                    return last_combined

        # Timeout
        self.last_response_links = last_links
        await ws_manager.send_log("warning", "⏱️ Timeout")
        await self._take_screenshot(f"timeout_{timestamp()}")
        return None

    def _is_own(self, text: str) -> bool:
        if not self._last_sent or not text:
            return False
        a = re.sub(r"\s+", " ", self._last_sent.strip().lower())
        b = re.sub(r"\s+", " ", text.strip().lower())
        return a in b or (len(a) > 15 and a[:50] == b[:50])

    async def _take_screenshot(self, name: str) -> str:
        try:
            await self._scroll_to_bottom()
            fn = f"{sanitize_filename(name)}.png"
            fp = os.path.join(app_config.screenshot_dir, fn)
            await self.page.screenshot(path=fp, full_page=True)
            with open(fp, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            await ws_manager.send_chat_message("system", f"📸 {name}", screenshot=f"data:image/png;base64,{b64}")
            return fp
        except Exception:
            return ""

    async def close(self):
        for r in [self.page, self.context, self.browser]:
            try:
                if r:
                    await r.close()
            except Exception:
                pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
