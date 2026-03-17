import asyncio
from playwright.async_api import async_playwright


class EanyLogin:
    def __init__(self, email: str, password: str, headless: bool = True):
        self.login_url = "https://eany.io/login/"
        self.email = email
        self.password = password
        self.headless = headless

    async def login(self) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto(self.login_url, wait_until="load")
            await asyncio.sleep(30)
            await page.click("button[id='CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll']")
            await page.fill("input[type='email']", self.email)
            await page.fill("input[type='password']", self.password)
            await page.click("button[type='submit']")
            await page.wait_for_load_state("load")
            await asyncio.sleep(30)

            cookies = await context.cookies()
            await browser.close()

            return "; ".join([f"{c['name']}={c['value']}" for c in cookies])
