
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.bybit.com/trade/usdt/BTCUSDT"

async def main():
    output = Path("screenshots")
    output.mkdir(exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox"]
        )

        page = await browser.new_page(
            viewport={"width": 1600, "height": 1000},
            locale="en-US"
        )

        try:
            response = await page.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=60000
            )

            print("HTTP status:",
                  response.status if response else "None")

            await page.wait_for_timeout(15000)
            print("Page title:", await page.title())
            print("Final URL:", page.url)

            clicked = False
            for locator in [
                page.get_by_text("15m", exact=True),
                page.get_by_text("15", exact=True)
            ]:
                try:
                    if await locator.count():
                        await locator.first.click(timeout=3000)
                        clicked = True
                        break
                except Exception:
                    pass

            print("15m selected by click:", clicked)
            await page.wait_for_timeout(5000)

            timestamp = datetime.now(
                timezone.utc
            ).strftime("%Y%m%d_%H%M%S")

            path = output / f"BTCUSDT_{timestamp}.png"
            await page.screenshot(
                path=str(path),
                full_page=False
            )

            print("Screenshot saved:", path)

            if not clicked:
                print("WARNING: Verify 15m manually.")

        finally:
            await browser.close()

asyncio.run(main())
