"""Take real screenshots of the running admin panel using Playwright."""
import asyncio
import time
import os
import sys
from playwright.async_api import async_playwright

ADMIN_URL = "http://localhost:3001"
API_URL = "http://localhost:8000"
SCREENSHOTS_DIR = "/home/user/Crypto-Paper-Trading-/screenshots"

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Viewport for desktop admin panel
VIEWPORT = {"width": 1440, "height": 900}

async def take_screenshots():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
            ]
        )
        context = await browser.new_context(viewport=VIEWPORT)
        page = await context.new_page()

        # ── 1. Admin Login Page ──────────────────────────────────────────────
        print("📸 Screenshot 1: Admin Login Page")
        await page.goto(f"{ADMIN_URL}/login", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1500)
        await page.screenshot(
            path=f"{SCREENSHOTS_DIR}/07_admin_login_page.png",
            full_page=False
        )
        print("  ✓ Saved 07_admin_login_page.png")

        # ── 2. Log in ────────────────────────────────────────────────────────
        print("🔐 Logging in as admin...")
        # Fill and submit the login form
        await page.fill('input[type="email"]', "admin@cryptopaper.com")
        await page.fill('input[type="password"]', "admin123")
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(3000)
        print(f"  Current URL after login: {page.url}")

        # ── 3. Admin Dashboard ───────────────────────────────────────────────
        print("📸 Screenshot 2: Admin Dashboard")
        await page.wait_for_timeout(2000)
        await page.screenshot(
            path=f"{SCREENSHOTS_DIR}/08_admin_dashboard_live.png",
            full_page=True
        )
        print("  ✓ Saved 08_admin_dashboard_live.png")

        # ── 4. Users Management ──────────────────────────────────────────────
        print("📸 Screenshot 3: Users Management Page")
        await page.goto(f"{ADMIN_URL}/users", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        await page.screenshot(
            path=f"{SCREENSHOTS_DIR}/09_admin_users_page.png",
            full_page=True
        )
        print("  ✓ Saved 09_admin_users_page.png")

        # ── 5. Positions Page ────────────────────────────────────────────────
        print("📸 Screenshot 4: Positions Management Page")
        await page.goto(f"{ADMIN_URL}/positions", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        await page.screenshot(
            path=f"{SCREENSHOTS_DIR}/10_admin_positions_page.png",
            full_page=True
        )
        print("  ✓ Saved 10_admin_positions_page.png")

        # ── 6. Logs Page ─────────────────────────────────────────────────────
        print("📸 Screenshot 5: Admin Logs Page")
        await page.goto(f"{ADMIN_URL}/logs", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        await page.screenshot(
            path=f"{SCREENSHOTS_DIR}/11_admin_logs_page.png",
            full_page=True
        )
        print("  ✓ Saved 11_admin_logs_page.png")

        # ── 7. Back to Dashboard (full overview) ─────────────────────────────
        print("📸 Screenshot 6: Dashboard overview (full scroll)")
        await page.goto(f"{ADMIN_URL}/", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(3000)
        await page.screenshot(
            path=f"{SCREENSHOTS_DIR}/12_admin_dashboard_full.png",
            full_page=True
        )
        print("  ✓ Saved 12_admin_dashboard_full.png")

        await browser.close()
        print("\n✅ All screenshots captured successfully!")
        print(f"📁 Saved to: {SCREENSHOTS_DIR}")


if __name__ == "__main__":
    asyncio.run(take_screenshots())
