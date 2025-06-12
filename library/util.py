import asyncio
import logging
from pathlib import Path


from .api import API
from . import crypt
from . import browser

async def login(
    cookie=None,
    cookie_file="cookies.json.enc",
    dont_store_cookies=False,
    browser_name="chromium"
) -> tuple[dict, dict, dict] | tuple[None, None, None]:
    """
    Logs in to Deezer using cookies or manual login if cookies are not provided or invalid.
    Args:
        cookie (str, optional): SID cookie to use for login. If None, try to load from file or manual login.
        cookie_file (str): Path to the cookie file.
        dont_store_cookies (bool): If True, do not store cookies to a file.
        browser_name (str): Which Playwright browser to use ("chromium", "firefox", "webkit")
    Returns:
        tuple: User data, cookies, and API request data if login is successful, None otherwise.
    """
    
    if cookie:
        cookie = {"sid": cookie}
    elif cookie_file and Path(cookie_file).exists():
        key = crypt.get_encryption_key()
        encrypted = Path(cookie_file).read_bytes()
        cookie = crypt.decrypt_cookies(encrypted, key)
        if cookie is None:
            logging.error("Failed to decrypt cookies. Please log in manually.")
            cookie = await browser.get_cookies_with_manual_login(cookie_file_path=cookie_file, dont_store_cookies=dont_store_cookies, browser_name=browser_name)
            if cookie is None:
                logging.error("Failed to retrieve cookies with manual login.")
                return None, None, None
    else:
        logging.info("No cookies found. Please log in manually.")
        cookie = await browser.get_cookies_with_manual_login(cookie_file_path=cookie_file, dont_store_cookies=dont_store_cookies, browser_name=browser_name)
        if cookie is None:
            logging.error("Failed to retrieve cookies with manual login.")
            return None, None, None

    async with API(cookie) as api:
        user_data = await api.validate_cookies()
        if not user_data:
            logging.warning("Cookies are invalid or expired. Attempting to log in manually.")
            cookie = await browser.get_cookies_with_manual_login(cookie_file_path=cookie_file, dont_store_cookies=dont_store_cookies, browser_name=browser_name)
            if cookie is not None:
                logging.info("Cookies successfully retrieved with manual login.")
                return await login(cookie=cookie, cookie_file=cookie_file, dont_store_cookies=dont_store_cookies, browser_name=browser_name)
        
            logging.error("Failed to retrieve cookies with manual login.")
            return None, None, None

        return user_data, cookie, api.request_data

async def deduplicate_playlist(playlist: list[int | str], deduplicate_by: int, _api: API, only_show: bool) -> tuple[list[dict], str, int | str] | tuple[None, str, int | str]:
    """
    Deduplicates a playlist by removing duplicate songs.
    Args:
        playlist (list): List containing playlist ID and name.
        deduplicate_by (int): Method to deduplicate by   
        _api (API): API instance to interact with Deezer.
        only_show (bool): If True, only shows which songs would be removed, no changes will be made to the playlist.
    Returns:
        list: Removed duplicates from the playlist if any, None on error. 
    """
    deduplicate_by_isrc = deduplicate_by in (1, 3)
    deduplicate_by_name = deduplicate_by in (2, 3)

    NAME = 0
    ID = 1

    duplicates = []
    songs = await _api.get_songs_in_playlist(playlist[ID])
    if not songs:
        logging.debug(f"Failed to retrieve songs for playlist {playlist[ID]}")
        return None, playlist[NAME], playlist[ID]
        
    if deduplicate_by_isrc: isrcs = set()
    if deduplicate_by_name: names = {}
    for song in songs:
        song_title = song["SNG_TITLE"] + song.get("VERSION", "")

        is_song_duplicate = False
        if deduplicate_by_isrc and song.get("ISRC"):
            if song["ISRC"] in isrcs:
                duplicates.append(song)
                is_song_duplicate = True
                logging.debug(f"Found duplicate song by ISRC: {song_title} in playlist {playlist[ID]}")
            else:
                isrcs.add(song["ISRC"])
        
        if deduplicate_by_name and not is_song_duplicate and song.get("ART_ID"):
            key = (song_title, song["ART_ID"])
            if key in names:
                duplicates.append(song)
                logging.debug(f"Found duplicate song by name: {song_title} by artist ID {song['ART_ID']} in playlist {playlist[ID]}")
            else:
                names[key] = song

    if duplicates:
        logging.debug(f"Found {len(duplicates)} duplicate songs by ISRC in playlist {playlist[ID]}")
        if only_show:
            return duplicates, playlist[NAME], playlist[ID]

        did_remove = await _api.remove_songs_from_playlist(playlist[ID], [song["SNG_ID"] for song in duplicates])
        if did_remove:
            logging.debug(f"Successfully actually removed {len(duplicates)} duplicate songs from playlist {playlist[ID]}")
            return duplicates, playlist[NAME], playlist[ID]
        
        logging.debug(f"Failed to remove duplicate songs from playlist {playlist[ID]}")
        return None, playlist[NAME], playlist[ID]
    else:
        logging.debug(f"No duplicate songs found by ISRC in playlist {playlist[ID]}")
        return None, playlist[NAME], playlist[ID]

async def deduplicate_playlists(playlists: list[tuple[int | str]], deduplicate_by: int, _api: API, only_show: bool=True) -> list[tuple[list[dict], str, int | str]] | None:
    """
    Deduplicates multiple playlists based on the specified method.
    Args:
        playlists (list): List of lists of playlist IDs and names to deduplicate.
        deduplicate_by (int): Method to deduplicate by:
        _api (API): API instance to interact with Deezer.
        only_show (bool): If True, only shows which songs would be removed, no changes will be made to the playlists.
    Returns:
        list: Removed duplicates from the playlists if any
    """


    if len(playlists) == 0:
        logging.warning("No playlists provided for deduplication.")
        return None
    
    if len(playlists) == 1:
        return [await deduplicate_playlist(playlists[0], deduplicate_by, _api, only_show)]
    
    playlists_removed_songs = []
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(deduplicate_playlist(playlist, deduplicate_by, _api, only_show)) for playlist in playlists]
        
    for task in tasks:
        result = task.result()
        if result:
            playlists_removed_songs.append(result)
    
    return playlists_removed_songs