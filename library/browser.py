import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import logging

import library.crypt as crypt

async def get_cookies_with_manual_login(url: str="https://account.deezer.com/login/", cookie_file_path:str ="cookies.json.enc") -> dict | None:
    """
    Opens a URL in a browser and waits until a cookie named 'account_id' is created.
    Then saves all cookies to a local file (encrypted) and closes the browser.
    
    Args:
        url (str): URL to navigate to
        cookie_file_path (str): Path where cookies will be saved (encrypted)
    
    Returns:
        dict: Dictionary of cookies if successful, None otherwise
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False, args=[
            "--disable-blink-features=AutomationControlled",
        ])
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(url)
        
        logging.debug("Waiting for login...")
        
        while browser.is_connected() and not page.is_closed():
            cookies = await context.cookies()
            account_cookie = next((cookie for cookie in cookies if cookie["name"] == "account_id"), None)
            
            if account_cookie:
                logging.debug("Account cookie found")
                break
                
            await asyncio.sleep(1)
        else:
            logging.debug("Browser got disconnected or page got closed before account cookie was set")
            await browser.close()
            return None
        
        await asyncio.sleep(1) # maybe some other cookies need time to be set, just in case
        cookies = cookies_to_aiohttp(await context.cookies())
        
        parent_dir = Path(__file__).parent.parent
        cookie_file_path = parent_dir/cookie_file_path

        key = crypt.get_encryption_key()
        encrypted = crypt.encrypt_cookies({ # only the sid cookie is needed
            "sid": cookies["sid"]
        }, key)
        Path(cookie_file_path).write_bytes(encrypted)
        logging.debug(f"Encrypted cookies saved to {cookie_file_path}")
        
        await browser.close()
        return cookies


def cookies_to_aiohttp(cookies: list) -> dict:
    """
    Converts Playwright cookies to aiohttp compatible format.
    
    Args:
        cookies (list): List of Playwright cookies
    
    Returns:
        dict: Dictionary of cookies for aiohttp
    """
    return {cookie["name"]: cookie["value"] for cookie in cookies}

if __name__ == "__main__":
    asyncio.run(get_cookies_with_manual_login("https://www.deezer.com"))