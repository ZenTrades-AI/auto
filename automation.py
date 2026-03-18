import os

from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()


def run_browser(data):
    print("🔥 run_browser STARTED", flush=True)

    # DYNAMIC FETCH: Completely mitigates Render deleting binaries between Build/Run phases.
    print("🛠 Ensuring Chromium is natively installed on the live runner...", flush=True)
    os.system("playwright install chromium")

    try:
        with sync_playwright() as p:
            # ✅ HEADLESS MODE (for server)
            # CRITICAL: Added args for Render's constrained architecture
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            # Add a spoofed User-Agent so Google doesn't instantly block the popup request due to Linux Headless detection
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            page = context.new_page()

            # =====================================
            # 🌐 OPEN LOGIN PAGE
            # =====================================
            print("🌐 Opening login page...")
            page.goto("https://srp.zentrades.pro/login")

            # =====================================
            # 🔐 GOOGLE LOGIN (POPUP HANDLING)
            # =====================================
            print("🔐 Clicking Google login...")
            
            # Google's Javascript dynamically rebuilds this button. Wait 5 seconds for it to stabilize!
            page.wait_for_timeout(5000)

            with page.expect_popup() as popup_info:
                # CRITICAL: Google ALWAYS hides their SSO login buttons inside a cross-domain iframe!
                # We MUST tell Playwright to tunnel into the iframe first, otherwise the element is permanently invisible to page locators!
                google_frame = page.frame_locator('iframe[title*="Sign in with Google"]').first
                google_frame.locator("#container-div").first.click()

            popup = popup_info.value
            popup.wait_for_load_state()

            popup.fill('input[type="email"]', os.getenv("EMAIL"))
            popup.click('button:has-text("Next")')

            popup.wait_for_timeout(3000)

            popup.fill('input[type="password"]', os.getenv("PASSWORD"))
            popup.click('button:has-text("Next")')

            print("⏳ Waiting for login...")
            popup.wait_for_event("close")

            page.wait_for_timeout(5000)
            print("✅ Login successful")

            # =====================================
            # 🚀 DELETE PAGE
            # =====================================
            page.goto("https://srp.zentrades.pro/delete")
            page.wait_for_timeout(5000)

            # =====================================
            # 🏢 SELECT COMPANY
            # =====================================
            print("🏢 Selecting company...")

            company_input = page.locator("#combo-box-demo")
            company_input.click()
            company_input.fill("E.A.S. Fire Services")

            page.wait_for_timeout(2000)
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")

            print("✅ Company selected")

            # =====================================
            # 📂 SELECT MODULE
            # =====================================
            print("📂 Selecting module...")

            page.locator('label:has-text("Modules")').locator('..').locator('div[role="button"]').click()
            page.wait_for_selector('li[role="option"]')

            page.locator('li[role="option"]:has-text("Customer")').click()

            print("✅ Module selected")
            # Explicitly wait for the Material UI dropdown popover to close gracefully
            try:
                page.locator('.MuiPopover-root').wait_for(state="hidden", timeout=5000)
            except:
                pass

            page.wait_for_timeout(3000)

            # =====================================
            # 🔍 SEARCH CUSTOMER
            # =====================================
            print("🔍 Searching customer...")

            customer_id = data.get("customer_id", "")
            print("📦 RAW CUSTOMER ID:", customer_id)

            # Use .first in case there are multiple Mui input variants hidden in the DOM
            search_input = page.locator('input[placeholder="Search Customer.."]').first
            
            search_input.wait_for(state="visible", timeout=15000)

            # Use force=True to bypass any sneaky hidden DOM layers
            search_input.click(force=True)
            search_input.fill(customer_id, force=True)
            search_input.press("Enter")

            print("✅ Searching:", customer_id)

            # Wait for delete button
            page.wait_for_selector('button:has-text("Delete")', timeout=15000)

            # =====================================
            # 🗑 DELETE
            # =====================================
            print("🗑 Clicking delete...")

            page.locator('button:has-text("Delete")').first.click()

            # =====================================
            # ✅ CONFIRM
            # =====================================
            print("✅ Confirming delete...")

            confirm_btn = page.locator(
                'button:has-text("Confirm"), button:has-text("Yes")'
            ).first

            confirm_btn.wait_for(state="visible", timeout=5000)
            confirm_btn.click()

            page.wait_for_timeout(5000)

            print("🎉 CUSTOMER DELETED SUCCESSFULLY")

            browser.close()

    except Exception as e:
        print("❌ ERROR:", str(e))