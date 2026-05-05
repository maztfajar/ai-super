"""
Browser Automation Tool
Memungkinkan agent AI untuk mengendalikan browser layaknya manusia.
Menggunakan Playwright untuk navigasi, klik, isi form, dan mengambil data.
"""

import asyncio
import os
import structlog
from typing import Optional, Dict, Any

log = structlog.get_logger()

class BrowserManager:
    """Manages persistent browser sessions for agents."""
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.contexts: Dict[str, Any] = {}
        self.pages: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def _ensure_started(self):
        if not self.playwright:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)

    async def get_page(self, session_id: str):
        """Ambil atau buat halaman browser untuk session_id tertentu."""
        session_id = session_id or "default"
        async with self._lock:
            await self._ensure_started()
            if session_id not in self.pages:
                context = await self.browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                self.contexts[session_id] = context
                self.pages[session_id] = page
            return self.pages[session_id]

    async def close_session(self, session_id: str):
        async with self._lock:
            if session_id in self.contexts:
                await self.contexts[session_id].close()
                del self.contexts[session_id]
                del self.pages[session_id]

_browser_manager = BrowserManager()


async def browser_navigate(url: str, session_id: str = None) -> str:
    """Buka halaman website."""
    try:
        page = await _browser_manager.get_page(session_id)
        # Tambahkan http jika belum ada
        if not url.startswith("http"):
            url = "https://" + url
            
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        return f"Berhasil membuka {url}. Judul halaman: {title}"
    except Exception as e:
        return f"Error navigasi ke {url}: {str(e)}"

async def browser_click(selector: str, session_id: str = None) -> str:
    """Klik elemen di halaman."""
    try:
        page = await _browser_manager.get_page(session_id)
        await page.click(selector, timeout=5000)
        await page.wait_for_load_state("networkidle", timeout=5000)
        return f"Berhasil mengklik elemen '{selector}'."
    except Exception as e:
        return f"Error klik elemen '{selector}': {str(e)}"

async def browser_type(selector: str, text: str, session_id: str = None) -> str:
    """Isi teks ke dalam field input."""
    try:
        page = await _browser_manager.get_page(session_id)
        await page.fill(selector, text, timeout=5000)
        return f"Berhasil mengisi teks ke '{selector}'."
    except Exception as e:
        return f"Error isi teks ke '{selector}': {str(e)}"

async def browser_extract_text(session_id: str = None) -> str:
    """Ambil teks (teks yang terlihat) dari halaman web saat ini."""
    try:
        page = await _browser_manager.get_page(session_id)
        # Ambil body text, hapus scripts dan styles
        text = await page.evaluate('''() => {
            const clone = document.body.cloneNode(true);
            const removeTags = clone.querySelectorAll('script, style, noscript, svg, img');
            removeTags.forEach(e => e.remove());
            return clone.innerText || clone.textContent;
        }''')
        # Batasi text agar tidak terlalu panjang (max 8000 chars)
        clean_text = " ".join(text.split())
        if len(clean_text) > 8000:
            clean_text = clean_text[:8000] + "... [Teks terpotong karena terlalu panjang]"
        return f"Teks halaman:\n{clean_text}"
    except Exception as e:
        return f"Error ekstrak teks: {str(e)}"

async def browser_screenshot(filename: str, session_id: str = None) -> str:
    """Ambil screenshot halaman dan simpan dengan nama file tertentu."""
    try:
        page = await _browser_manager.get_page(session_id)
        
        # Path screenshot
        base_dir = os.path.expanduser(f"~/projects/{session_id[:8] if session_id else 'default'}")
        os.makedirs(base_dir, exist_ok=True)
        filepath = os.path.join(base_dir, filename)
        if not filepath.endswith(".png"):
            filepath += ".png"
            
        await page.screenshot(path=filepath, full_page=True)
        return f"Berhasil mengambil screenshot. Disimpan di {filepath}"
    except Exception as e:
        return f"Error mengambil screenshot: {str(e)}"
