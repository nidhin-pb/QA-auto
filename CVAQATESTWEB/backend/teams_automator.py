"""
Teams Browser Automation v6.2-patch2
EXACTLY your original v6.2 with only 2 changes:
1. Added loading phrases: "crafting...", "analyzing details..."
2. Fixed duplicate reply timeout: old hashes tracked separately
"""
import os
import sys
import asyncio
import base64
import re
import hashlib
from typing import Optional, List, Set
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from config import app_config
from utils import ensure_dir, timestamp, sanitize_filename, extract_urls_from_text
from websocket_manager import ws_manager


LOADING_PHRASES = [
    "processing your request", "please hold on", "⏳",
    "typing", "please wait", "one moment", "working on it",
    "i'm thinking", "thinking and analyzing",
    "analyzing your request", "gathering information for you",
    "gathering information", "working on your request",
    # NEW: additional loading phrases found during testing
    "crafting your personalized response", "crafting your response",
    "crafting your", "personalized response",
    "analyzing details and gathering insights",
    "analyzing details", "gathering insights",
]

CARD_INDICATORS = [
    "card - access it on",
    "go.skype.com/cards.unsupported",
    "complete this request",
    "view details",
    "view in servicenow",
    "start chat handover",
]


def make_hash(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())[:500]
    return hashlib.md5(cleaned.encode("utf-8", errors="ignore")).hexdigest()[:16]


def is_loading(text: str) -> bool:
    t = (text or "").lower().strip()
    # Check for emoji-only or very short
    if len(t) < 80:
        if any(p in t for p in LOADING_PHRASES):
            return True
    # Also catch short emoji-heavy strings
    if len(t) <= 5:
        return True
    # Catch patterns like "⚙️" "✨" "⏳" alone or with short text
    stripped = re.sub(r'[^\w\s]', '', t).strip()
    if len(stripped) < 10 and any(c in t for c in ['⚙️', '✨', '⏳', '🔄', '💭']):
        return True
    return False


def is_card_message(text: str) -> bool:
    t = (text or "").lower().strip()
    return any(ind in t for ind in CARD_INDICATORS)


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
        self._seen_item_keys: Set[str] = set()
        self._last_listitem_count = 0
        self._last_sent: str = ""
        self._sent_messages: List[str] = []  # NEW: track ALL sent messages

        self._seen_links: Set[str] = set()
        self.last_response_links: List[str] = []

        ensure_dir(app_config.screenshot_dir)

    def _is_teams_url(self, url: str) -> bool:
        u = (url or "").lower()
        return ("teams.microsoft.com" in u) or ("teams.cloud.microsoft" in u)

    async def initialize(self):
        await ws_manager.send_log("info", "Initializing browser...")
        self.playwright = await async_playwright().start()

        for ch, nm in [("chrome", "Chrome"), ("msedge", "Edge"), (None, "Chromium")]:
            try:
                args = ["--disable-blink-features=AutomationControlled"]
                if sys.platform == "linux":
                    args.append("--no-sandbox")
                kw = {"headless": app_config.headless, "slow_mo": app_config.browser_slow_mo, "args": args}
                if ch:
                    kw["channel"] = ch
                self.browser = await self.playwright.chromium.launch(**kw)
                await ws_manager.send_log("info", f"Launched {nm}")
                break
            except Exception:
                continue
        else:
            self.browser = await self.playwright.firefox.launch(headless=app_config.headless, slow_mo=app_config.browser_slow_mo)
            await ws_manager.send_log("info", "Launched Firefox")

        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="America/New_York",
            ignore_https_errors=True,
            device_scale_factor=1,
        )
        self.context.set_default_timeout(30000)
        self.page = await self.context.new_page()
        self.page.on("pageerror", lambda _: None)
        self.page.on("console", lambda _: None)

    async def login(self, email: str, password: str) -> bool:
        try:
            await self.page.goto(app_config.teams.teams_url, wait_until="load", timeout=60000)
            await asyncio.sleep(5)

            if not any(d in (self.page.url or "") for d in ["login.microsoftonline.com", "login.live.com"]):
                try:
                    await self.page.locator('a:has-text("Sign in"), button:has-text("Sign in")').first.click(timeout=10000)
                    await asyncio.sleep(5)
                except Exception:
                    pass

            await self._login_flow(email, password)

            await ws_manager.send_log("info", f"After login URL: {self.page.url}")
            ok = await self._wait_teams_quick()

            self.is_logged_in = True
            await ws_manager.send_log("info", "✅ Logged in!")
            return True if ok else True

        except Exception as e:
            await ws_manager.send_log("error", f"Login failed: {str(e)}")
            return False

    async def _login_flow(self, email, password):
        await asyncio.sleep(2)

        for _ in range(10):
            for s in ['input[name="loginfmt"]', '#i0116', 'input[type="email"]']:
                try:
                    inp = self.page.locator(s).first
                    if await inp.is_visible(timeout=2000):
                        await inp.fill(email)
                        await self._submit()
                        await asyncio.sleep(4)
                        raise StopIteration
                except StopIteration:
                    break
                except Exception:
                    continue
            else:
                await asyncio.sleep(2)
                continue
            break

        for _ in range(10):
            for s in ['input[name="passwd"]', '#i0118', 'input[type="password"]']:
                try:
                    inp = self.page.locator(s).first
                    if await inp.is_visible(timeout=2000):
                        await inp.fill(password)
                        await self._submit()
                        await asyncio.sleep(5)
                        raise StopIteration
                except StopIteration:
                    break
                except Exception:
                    continue
            else:
                await asyncio.sleep(2)
                continue
            break

        await asyncio.sleep(2)
        for _ in range(8):
            for s in ['#idSIButton9', 'input[value="Yes"]', 'button:has-text("Yes")', 'button:has-text("Accept")', 'button:has-text("Continue")']:
                try:
                    btn = self.page.locator(s).first
                    if await btn.is_visible(timeout=1500):
                        await btn.click()
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue
            if self._is_teams_url(self.page.url):
                break

    async def _submit(self):
        for s in ['#idSIButton9', 'input[type="submit"]']:
            try:
                btn = self.page.locator(s).first
                if await btn.is_visible(timeout=1500):
                    await btn.click()
                    return
            except Exception:
                continue
        await self.page.keyboard.press("Enter")

    async def _dismiss(self):
        for s in [
            'button:has-text("Use the web app instead")',
            'button:has-text("Continue")',
            'button:has-text("Got it")',
            'button:has-text("OK")',
            'button:has-text("Dismiss")',
            'button:has-text("Skip")',
            'button:has-text("Maybe later")',
            'button[aria-label="Close"]',
        ]:
            try:
                btn = self.page.locator(s).first
                if await btn.is_visible(timeout=600):
                    await btn.click()
                    await asyncio.sleep(0.3)
            except Exception:
                continue

    async def _wait_teams_quick(self) -> bool:
        await self._dismiss()
        selectors = [
            'button[aria-label="Chat"]',
            '#app-bar-chat-button',
            'button[aria-label="Apps"]',
            'nav[role="navigation"]',
            '[data-tid="app-bar"]',
        ]
        for i in range(15):
            await asyncio.sleep(2)
            if not self._is_teams_url(self.page.url):
                continue
            if i % 5 == 0:
                await self._dismiss()
            for s in selectors:
                try:
                    if await self.page.locator(s).first.is_visible(timeout=1000):
                        return True
                except Exception:
                    continue
        await ws_manager.send_log("warning", f"Teams UI not detected quickly; continuing. URL={self.page.url}")
        return False

    async def open_cva_chat(self) -> bool:
        cva = app_config.teams.cva_app_name
        await asyncio.sleep(1)

        for s in ['button[aria-label="Chat"]', '#app-bar-chat-button', '[data-tid="app-bar-chat-button"]']:
            try:
                btn = self.page.locator(s).first
                if await btn.is_visible(timeout=4000):
                    await btn.click()
                    await asyncio.sleep(2)
                    break
            except Exception:
                continue

        for t in [cva, "IT Servicedesk", "Servicedesk", "Service desk"]:
            try:
                item = self.page.locator(f'span:has-text("{t}")').first
                if await item.is_visible(timeout=3000):
                    await item.click()
                    await asyncio.sleep(2)
                    self.is_cva_open = True
                    await self.reset_chat_context()
                    await ws_manager.send_log("info", f"✅ Opened CVA chat: {t}")
                    return True
            except Exception:
                continue

        for s in ['input[placeholder*="Search"]', 'input[aria-label*="Search"]']:
            try:
                search = self.page.locator(s).first
                if await search.is_visible(timeout=2000):
                    await search.click()
                    await asyncio.sleep(0.2)
                    await search.fill(cva)
                    await asyncio.sleep(1)
                    await self.page.keyboard.press("Enter")
                    await asyncio.sleep(2)

                    item = self.page.locator(f'span:has-text("{cva}")').first
                    if await item.is_visible(timeout=3000):
                        await item.click()
                        await asyncio.sleep(2)
                        self.is_cva_open = True
                        await self.reset_chat_context()
                        await ws_manager.send_log("info", f"✅ Opened CVA chat via search: {cva}")
                        return True
            except Exception:
                continue

        await ws_manager.send_log("error", "Failed to open CVA chat. Verify CVA App Name.")
        await self._take_screenshot(f"open_cva_failed_{timestamp()}")
        return False

    # ---------- v6.2 text extraction (PROVEN WORKING — unchanged) ----------

    async def _get_texts(self) -> List[str]:
        texts: List[str] = []

        for sel in ['[data-tid="chat-pane-message"]', 'div[class*="message-body-content"]', 'div[class*="message-body"]']:
            try:
                els = self.page.locator(sel)
                count = await els.count()
                if count > 0:
                    for i in range(count):
                        try:
                            t = await els.nth(i).inner_text(timeout=800)
                            if t and t.strip() and len(t.strip()) > 1:
                                texts.append(t.strip())
                        except Exception:
                            continue
                    if texts:
                        return texts
            except Exception:
                continue

        try:
            els = self.page.locator('div[role="listitem"]')
            count = await els.count()
            for i in range(count):
                try:
                    t = await els.nth(i).inner_text(timeout=800)
                    if t and t.strip() and len(t.strip()) > 3:
                        texts.append(t.strip())
                except Exception:
                    continue
            if texts:
                return texts
        except Exception:
            pass

        try:
            for sel in ['div[class*="chat-body"]', 'div[role="main"]']:
                try:
                    area = self.page.locator(sel).first
                    if await area.is_visible(timeout=1500):
                        full = await area.inner_text(timeout=3000)
                        if full and len(full) > 20:
                            parts = re.split(r'\n{3,}', full)
                            texts = [p.strip() for p in parts if p.strip() and len(p.strip()) > 5]
                            if texts:
                                return texts
                except Exception:
                    continue
        except Exception:
            pass

        return texts

    async def _check_for_cards(self) -> List[str]:
        card_texts = []
        try:
            card_selectors = [
                'div[class*="ac-container"]',
                'div[class*="adaptive-card"]',
                'div[class*="card-content"]',
                'div[class*="ac-textBlock"]',
                'div[class*="card"]',
            ]
            for sel in card_selectors:
                try:
                    els = self.page.locator(sel)
                    count = await els.count()
                    for i in range(count):
                        try:
                            t = await els.nth(i).inner_text(timeout=800)
                            if t and t.strip() and len(t.strip()) > 10:
                                card_texts.append(t.strip())
                        except Exception:
                            continue
                except Exception:
                    continue

            for sel in [
                'button:has-text("Complete this request")',
                'button:has-text("View in ServiceNow")',
                'a:has-text("Complete this request")',
                'a:has-text("View in ServiceNow")',
            ]:
                try:
                    btn = self.page.locator(sel).first
                    if await btn.is_visible(timeout=800):
                        parent_text = await btn.evaluate(
                            'el => el.closest("div")?.innerText || ""'
                        )
                        if parent_text and len(parent_text) > 10:
                            card_texts.append(parent_text.strip())
                except Exception:
                    continue

        except Exception:
            pass
        return card_texts

    async def _get_visible_links(self) -> List[str]:
        try:
            urls = await self.page.evaluate(
                """() => {
                    const out = new Set();
                    const containers = [
                      ...document.querySelectorAll('div[role="listitem"]'),
                      ...document.querySelectorAll('[data-tid="chat-pane-message"]'),
                      ...document.querySelectorAll('div[class*="message-body"]')
                    ];
                    const recent = containers.slice(-40);
                    const norm = (u) => {
                      if (!u) return '';
                      try { return new URL(u, window.location.href).href; }
                      catch(e) { return ''; }
                    };
                    for (const c of recent) {
                      c.querySelectorAll('a[href]').forEach(a => {
                        const u = norm(a.getAttribute('href') || a.href);
                        if (u.startsWith('http')) out.add(u);
                      });
                      c.querySelectorAll('[role="link"]').forEach(el => {
                        const u = el.getAttribute('href') || el.getAttribute('data-url') || el.getAttribute('data-href') || (el.dataset && (el.dataset.url || el.dataset.href)) || '';
                        const nu = norm(u);
                        if (nu.startsWith('http')) out.add(nu);
                      });
                      c.querySelectorAll('button').forEach(b => {
                        const u = b.getAttribute('data-url') || b.getAttribute('data-href') || (b.dataset && (b.dataset.url || b.dataset.href)) || '';
                        const nu = norm(u);
                        if (nu.startsWith('http')) out.add(nu);
                      });
                    }
                    return Array.from(out);
                }"""
            )
            if not isinstance(urls, list):
                return []
            cleaned = []
            for u in urls:
                if u and isinstance(u, str) and u.startswith("http") and u not in cleaned:
                    cleaned.append(u)
            return cleaned
        except Exception:
            return []

    async def reset_chat_context(self):
        await asyncio.sleep(1)
        self._seen_hashes.clear()
        self._seen_item_keys.clear()
        self._last_sent = ""
        self._sent_messages.clear()
        self.last_response_links = []

        try:
            self._last_listitem_count = await self.page.locator('div[role="listitem"]').count()
        except Exception:
            self._last_listitem_count = 0

        self._seen_links.clear()
        for u in await self._get_visible_links():
            self._seen_links.add(u)

        await ws_manager.send_log("info", "Reset: ready for next test")

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

    async def upload_attachments(self, paths: List[str]) -> bool:
        import os

        paths = [p for p in (paths or []) if p and os.path.exists(p)]
        if not paths:
            return False

        filenames = [os.path.basename(p) for p in paths]
        await ws_manager.send_log("info", f"📎 Uploading {len(paths)} attachment(s): {', '.join(filenames)}")

        try:
            inp = await self._find_input()
            if inp:
                await inp.click()
                await asyncio.sleep(0.4)
        except Exception:
            pass

        async def verify_file_visible(timeout_s: int = 12) -> bool:
            for _ in range(timeout_s):
                try:
                    body = await self.page.inner_text("body")
                    low = (body or "").lower()
                    if all(fn.lower() in low for fn in filenames):
                        return True
                except Exception:
                    pass
                await asyncio.sleep(1)
            return False

        async def try_file_inputs() -> bool:
            try:
                inputs = self.page.locator('input[type="file"]')
                c = await inputs.count()
                await ws_manager.send_log("info", f"Debug: input[type=file] count={c}")
                if c <= 0:
                    return False
                for idx in [c - 1, 0]:
                    try:
                        await inputs.nth(idx).set_input_files(paths)
                        await asyncio.sleep(2)
                        if await verify_file_visible(8):
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            return False

        async def try_attach_button_and_chooser() -> bool:
            for sel in ['button[aria-label*="Attach"]', 'button[title*="Attach"]', 'button:has-text("Attach")', 'button:has-text("Attach file")']:
                try:
                    btn = self.page.locator(sel).first
                    if await btn.is_visible(timeout=1200):
                        try:
                            async with self.page.expect_file_chooser(timeout=3000) as fc_info:
                                await btn.click()
                            fc = await fc_info.value
                            await fc.set_files(paths)
                            await asyncio.sleep(2)
                            if await verify_file_visible(10):
                                return True
                        except Exception:
                            await btn.click()
                            await asyncio.sleep(1)
                            if await try_file_inputs():
                                return True
                except Exception:
                    continue
            return False

        async def try_plus_menu_upload() -> bool:
            for sel in ['button[aria-label*="Actions and apps"]', 'button[title*="Actions and apps"]', 'button[aria-label*="More actions"]', 'button[title*="More actions"]', 'button[aria-label*="Apps"]', 'button[title*="Apps"]']:
                try:
                    b = self.page.locator(sel).first
                    if await b.is_visible(timeout=1200):
                        await b.click()
                        await asyncio.sleep(1)
                        break
                except Exception:
                    continue
            else:
                return False

            for sel in ['div[role="menuitem"]:has-text("Upload from this device")', 'div[role="menuitem"]:has-text("Upload")', 'div[role="menuitem"]:has-text("Attach file")', 'div[role="menuitem"]:has-text("Attach")', 'button:has-text("Upload from this device")', 'button:has-text("Upload")', 'button:has-text("Attach file")', 'button:has-text("Attach")']:
                try:
                    item = self.page.locator(sel).first
                    if not await item.is_visible(timeout=1200):
                        continue
                    try:
                        async with self.page.expect_file_chooser(timeout=3000) as fc_info:
                            await item.click()
                        fc = await fc_info.value
                        await fc.set_files(paths)
                        await asyncio.sleep(2)
                        if await verify_file_visible(10):
                            return True
                    except Exception:
                        await item.click()
                        await asyncio.sleep(1)
                        try:
                            sub = self.page.locator('div[role="menuitem"]:has-text("Upload from this device"), button:has-text("Upload from this device")').first
                            if await sub.is_visible(timeout=1500):
                                try:
                                    async with self.page.expect_file_chooser(timeout=3000) as fc_info2:
                                        await sub.click()
                                    fc2 = await fc_info2.value
                                    await fc2.set_files(paths)
                                    await asyncio.sleep(2)
                                    if await verify_file_visible(10):
                                        return True
                                except Exception:
                                    await sub.click()
                                    await asyncio.sleep(1)
                        except Exception:
                            pass
                        if await try_file_inputs():
                            return True
                except Exception:
                    continue
            return False

        if await try_file_inputs():
            await ws_manager.send_log("info", "✅ Attachment uploaded via input[type=file]")
            return True
        if await try_attach_button_and_chooser():
            await ws_manager.send_log("info", "✅ Attachment uploaded via Attach button / chooser")
            return True
        if await try_plus_menu_upload():
            await ws_manager.send_log("info", "✅ Attachment uploaded via '+' menu")
            return True

        await ws_manager.send_log("warning", "❌ Attachment upload failed in Teams UI")
        await self._take_screenshot(f"attach_failed_{timestamp()}")
        return False

    async def send_message(self, message: str, attachments: Optional[List[str]] = None) -> bool:
        try:
            self._last_sent = message
            self._sent_messages.append(message)

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
            await asyncio.sleep(0.15)

            if attachments:
                ok = await self.upload_attachments(attachments)
                if not ok:
                    await ws_manager.send_log("warning", "Attachment upload failed; continuing without attachment.")

            await self.page.keyboard.type(message, delay=25)
            await asyncio.sleep(0.4)

            await self._take_screenshot(f"msg_typed_{timestamp()}")

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

    def _is_own(self, text: str) -> bool:
        """Check if text matches ANY message we sent in this test."""
        if not text:
            return False
        b = re.sub(r'\s+', ' ', text.strip().lower())

        for sent in self._sent_messages:
            a = re.sub(r'\s+', ' ', sent.strip().lower())
            if a == b:
                return True
            if b.startswith(a) and (len(b) - len(a)) <= 15:
                return True
            if len(a) > 20 and b[:min(len(b), 100)] == a[:min(len(a), 100)]:
                return True
        return False

    async def _read_last_message(self) -> Optional[dict]:
        """
        Read the LAST message in the chat using JavaScript.
        Returns {text, links} or None.
        This is the most reliable way to get CVA's latest reply.
        """
        try:
            result = await self.page.evaluate("""
                () => {
                    // Try multiple selectors to find message containers
                    const selectors = [
                        '[data-tid="chat-pane-message"]',
                        'div[class*="message-body-content"]',
                        'div[class*="message-body"]',
                        'div[role="listitem"]',
                    ];

                    let elements = [];
                    for (const sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        if (els.length > elements.length) {
                            elements = Array.from(els);
                        }
                    }

                    if (elements.length === 0) return null;

                    // Get the LAST element
                    const last = elements[elements.length - 1];
                    const text = (last.innerText || '').trim();

                    // Extract links
                    const links = [];
                    const norm = (u) => {
                        if (!u) return '';
                        try { return new URL(u, window.location.href).href; }
                        catch(e) { return ''; }
                    };
                    last.querySelectorAll('a[href]').forEach(a => {
                        const u = norm(a.getAttribute('href') || a.href);
                        if (u && u.startsWith('http')) links.push(u);
                    });
                    last.querySelectorAll('[role="link"]').forEach(rl => {
                        const u = norm(rl.getAttribute('href') || rl.getAttribute('data-url') || '');
                        if (u && u.startsWith('http')) links.push(u);
                    });

                    return { text: text, links: links };
                }
            """)
            return result if isinstance(result, dict) else None
        except Exception:
            return None

    async def _extract_links_from_listitem(self, item_locator) -> list:
        try:
            links = await item_locator.evaluate(
                """(el) => {
                    const out = new Set();
                    const norm = (u) => {
                      if (!u) return "";
                      try { return new URL(u, window.location.href).href; } catch(e) { return ""; }
                    };
                    el.querySelectorAll('a[href]').forEach(a => {
                      const u = norm(a.getAttribute('href') || a.href);
                      if (u.startsWith('http')) out.add(u);
                    });
                    el.querySelectorAll('[role="link"]').forEach(n => {
                      const u = n.getAttribute('href') || n.getAttribute('data-url') || n.getAttribute('data-href') || "";
                      const nu = norm(u);
                      if (nu.startsWith('http')) out.add(nu);
                    });
                    el.querySelectorAll('button').forEach(b => {
                      const u = b.getAttribute('data-url') || b.getAttribute('data-href') || "";
                      const nu = norm(u);
                      if (nu.startsWith('http')) out.add(nu);
                    });
                    return Array.from(out);
                }"""
            )
            return links if isinstance(links, list) else []
        except Exception:
            return []

    async def wait_for_response(self, timeout: int = None) -> Optional[str]:
        """
        SIMPLE AND RELIABLE: Read the LAST message in the chat.
        If it's not our sent message and not a loading indicator, it's CVA's reply.
        Works with identical replies because we're reading position (last), not content.
        """
        timeout = timeout or app_config.max_wait_for_response
        await ws_manager.send_log("info", f"Waiting for CVA response ({timeout}s)...")

        elapsed = 0.0
        interval = float(app_config.message_check_interval)
        found_loading = False

        last_good_text = ""
        quiet = 0
        quiet_required = 3

        resp_links = []

        def is_interim(text: str) -> bool:
            t = (text or "").lower()
            return any(p in t for p in [
                "i'm thinking", "thinking and analyzing",
                "analyzing your request", "gathering information",
                "gathering information for you",
                "crafting your personalized response",
                "crafting your response", "crafting your",
                "analyzing details and gathering insights",
                "analyzing details", "gathering insights",
            ])

        def is_meaningful(text: str) -> bool:
            if not text:
                return False
            if is_loading(text) or is_interim(text):
                return False
            if len(text) >= 30:
                return True
            t = text.lower()
            if any(k in t for k in [
                "i can only", "hello", "sorry", "thank",
                "step", "?", "pankaj", "assist",
            ]):
                return True
            return False

        while elapsed < timeout:
            await asyncio.sleep(interval)
            elapsed += interval

            # Read the LAST message in the chat
            last_msg = await self._read_last_message()
            if not last_msg:
                if last_good_text:
                    quiet += 1
                    if quiet >= quiet_required:
                        break
                continue

            text = (last_msg.get("text") or "").strip()
            links = last_msg.get("links", [])

            if not text:
                if last_good_text:
                    quiet += 1
                    if quiet >= quiet_required:
                        break
                continue

            # Is it our own message? Keep waiting.
            if self._is_own(text):
                if last_good_text:
                    quiet += 1
                    if quiet >= quiet_required:
                        break
                continue

            # Is it loading/interim? Keep waiting.
            if is_loading(text) or is_interim(text):
                if not found_loading:
                    found_loading = True
                    await ws_manager.send_log("info", "CVA is processing... ⏳")
                continue

            # It's a real message from CVA!
            if is_meaningful(text):
                if text != last_good_text:
                    # New or updated response
                    last_good_text = text
                    resp_links = links
                    quiet = 0
                    quiet_required = 2
                else:
                    # Same text as before, count as quiet
                    quiet += 1
                    if quiet >= quiet_required:
                        break
            else:
                # Not meaningful yet
                if last_good_text:
                    quiet += 1
                    if quiet >= quiet_required:
                        break

        if last_good_text:
            await ws_manager.send_log("info", f"CVA responded ({len(last_good_text)} chars)")
            await ws_manager.send_chat_message("cva", last_good_text[:2000])
            await self._take_screenshot(f"response_{timestamp()}")

            text_links = extract_urls_from_text(last_good_text)
            merged = []
            for u in (resp_links + text_links):
                if u and u not in merged:
                    merged.append(u)
            self.last_response_links = merged

            return last_good_text

        await ws_manager.send_log("warning", "⏱️ Timeout")
        await self._take_screenshot(f"timeout_{timestamp()}")
        self.last_response_links = []
        return None

    async def _take_screenshot(self, name: str) -> str:
        try:
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
