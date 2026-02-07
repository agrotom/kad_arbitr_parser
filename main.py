import asyncio
import json
import sys

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from bs4 import BeautifulSoup
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from playwright.async_api import async_playwright, Route

MAX_TRIES = 2

context = None
playwright = None

is_started = False

restart_lock = asyncio.Lock()

MAX_CONCURRENT_JOBS = 2

job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

app = FastAPI()

class PdfState:
    def __init__(self, max_tries=5):
        self.file: bytes | None = None
        self.captured = False
        self.tries = 0
        self.max_tries = max_tries
        self.event = asyncio.Event()

async def handle_pdf(route: Route, state: PdfState):
    if state.captured or state.tries >= state.max_tries:
        await route.continue_()
        return

    response = await route.fetch()
    ctype = response.headers.get("content-type", "")

    if response.status == 200 and "application/pdf" in ctype:
        state.file = await response.body()

        state.captured = True
        state.event.set()

    state.tries += 1
    await route.fulfill(response=response)

async def start_browser():
    global context, playwright

    if context and context.browser.is_connected():
        return

    print("Starting browser...")

    if playwright:
        try:
            await playwright.stop()
        except:
            pass

    playwright = await async_playwright().start()

    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=r"C:\Users\agrotom\AppData\Local\Google\Chrome\User Data\Profile 2",
        channel="chrome",
        headless=False,
        accept_downloads=True,
        args=[
			"--no-sandbox",
			"--disable-dev-shm-usage"
            '--disable-features=DevToolsDebuggingRestrictions',
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
        ]
    )

async def restart_browser():
    global context, playwright

    async with restart_lock:
        browser = context.browser if context else None

        if context and context.browser.is_connected():
            return
        
        print("Restarting browser...")

        try:
            if browser:
                await browser.close()
        except:
            pass

        try:
            if playwright:
                await playwright.stop()
        except:
            pass

        await start_browser()

@app.on_event("startup")
async def startup():
    await start_browser()

@app.get('/getFile')
async def get_file(url: str, pos: int = 0):
    global context

    page_created = False

    async with job_semaphore:
        for _ in range(MAX_TRIES):
            try:
                page = await context.new_page()

                page_created = True
                
                state = PdfState()

                await page.route(
                    "**/*.pdf*",
                    lambda route: handle_pdf(route, state)
                )

                await page.goto(url, timeout=30000)

                await asyncio.wait_for(state.event.wait(), timeout=15)

            except Exception as e:
                print("Error occured", e)

                if context and context.browser.is_connected() == False:
                    await restart_browser()
                    continue

                return Response(None, status_code=500)
            
            finally:
                if page_created:
                    await page.close()

            if state.file == None:
                return Response(status_code=404)
            
            return Response(state.file, media_type="application/pdf")
    
@app.get('/getPage')
async def get_page(url: str):
    global context
    source = None

    page_created = False

    async with job_semaphore:
        for _ in range(MAX_TRIES):
            try:
                page = await context.new_page()

                page_created = True

                await page.goto(url, timeout=30000)

                html = await page.content()
                soup = BeautifulSoup(html, "html.parser")
                if soup.find('div', class_='b-offline-content') != None: # Проверка на отсутствие ресурса
                        await page.close()
                        return Response(status_code=410)

                await page.wait_for_selector("span.js-case-header-case_num", timeout=30000)

                max_attempt_count = 40

                pdf_links = []

                for _ in range(max_attempt_count):
                    await page.click("div[title='Нажмите, чтобы ознакомиться с полной хронологией дела.']") # Раскрыть список хронологии дела
                    await page.wait_for_selector("div[class='b-chrono-item-header js-chrono-item-header page-break b-chrono-item-header-expanded']", timeout=60000)

                    html = await page.content()
                    soup = BeautifulSoup(html, "html.parser")

                    if soup.find('span', class_='js-case-header-case_num') != None: # Проверка на загрузку страницы
                        source = html
                        pdf_links = [a['href'].replace("Kad/PdfDocument", "Document/Pdf") for a in soup.find_all('a', href=True) if '.pdf' in a['href'].lower()]
                        break

                    asyncio.sleep(0.5)

            except Exception as e:
                print("Error occured", e)

                if context and context.browser.is_connected() == False:
                    await restart_browser()
                    continue
                
                return Response(None, status_code=500)
            
            finally:
                if page_created:
                    await page.close()

            return HTMLResponse(json.dumps({ 'source': source, 'pdf_links': pdf_links }), media_type="application/json")