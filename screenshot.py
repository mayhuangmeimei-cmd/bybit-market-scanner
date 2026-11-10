
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from playwright.async_api import async_playwright

# Bybit BTCUSDT 永续合约
URL = "https://www.bybit.com/trade/usdt/BTCUSDT"

# 截图保存目录
OUTPUT_DIR = Path("screenshots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def main():
    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-http2"
            ]
        )

        page = await browser.new_page(
            viewport={
                "width": 1600,
                "height": 1000
            },
            locale="en-US"
        )

        try:
            print("Opening Bybit...")
            print("Target URL:", URL)

            # 第一步：尝试打开 Bybit
            try:
                response = await page.goto(
                    URL,
                    wait_until="commit",
                    timeout=60000
                )

                status = (
                    response.status
                    if response else None
                )

                print("HTTP status:", status)

            except Exception as e:
                print("Navigation error:", str(e))

                error_path = (
                    OUTPUT_DIR /
                    f"bybit_error_{timestamp}.png"
                )

                try:
                    await page.screenshot(
                        path=str(error_path),
                        full_page=False,
                        timeout=10000
                    )
                    print("Error screenshot:", error_path)
                except Exception as screenshot_error:
                    print(
                        "Screenshot failed:",
                        str(screenshot_error)
                    )

                raise

            # HTTP 错误时保存截图并报告失败
            if status is not None and status >= 400:
                print("HTTP request rejected:", status)

                await page.screenshot(
                    path=str(
                        OUTPUT_DIR /
                        f"bybit_http_{status}_{timestamp}.png"
                    ),
                    full_page=False
                )

                raise RuntimeError(
                    f"Bybit returned HTTP {status}"
                )

            # 第二步：等待图表加载
            print("Waiting for chart...")
            await page.wait_for_timeout(15000)

            print("Page title:", await page.title())
            print("Final URL:", page.url)

            # 第三步：尝试选择 15m
            print("Selecting 15m timeframe...")

            clicked = False

            selectors = [
                page.get_by_text("15m", exact=True),
                page.get_by_text("15", exact=True)
            ]

            for locator in selectors:
                try:
                    if await locator.count() > 0:
                        await locator.first.click(
                            timeout=3000
                        )
                        clicked = True
                        print("15m click attempted")
                        break
                except Exception as e:
                    print("Selector failed:", str(e)[:150])

            if not clicked:
                print(
                    "WARNING: 15m selector not found."
                )

            await page.wait_for_timeout(5000)

            # 第四步：保存最终截图
            screenshot_path = (
                OUTPUT_DIR /
                f"BTCUSDT_15m_{timestamp}.png"
            )

            await page.screenshot(
                path=str(screenshot_path),
                full_page=False,
                timeout=15000
            )

            print("Screenshot saved:", screenshot_path)
            print(
                "IMPORTANT: Check chart and timeframe "
                "manually before accepting the result."
            )

        except Exception as e:
            print("TEST FAILED:", str(e))
            raise

        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
