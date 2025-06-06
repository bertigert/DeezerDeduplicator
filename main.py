import asyncio
from pathlib import Path
import logging
import argparse

from tabulate import tabulate

from library.api import API, MV 
from library import browser
from library import crypt


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


async def login(
    cookie=None,
    cookie_file="cookies.json.enc",
    dont_store_cookies=False
) -> tuple[dict, dict, dict] | tuple[None, None, None]:
    """
    Logs in to Deezer using cookies or manual login if cookies are not provided or invalid.
    Args:
        cookie (str, optional): SID cookie to use for login. If None, try to load from file or manual login.
        cookie_file (str): Path to the cookie file.
        dont_store_cookies (bool): If True, do not store cookies to a file.
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
            cookie = await browser.get_cookies_with_manual_login(cookie_file_path=cookie_file, dont_store_cookies=dont_store_cookies)
            if cookie is None:
                logging.error("Failed to retrieve cookies with manual login.")
                return None, None, None
    else:
        logging.info("No cookies found. Please log in manually.")
        cookie = await browser.get_cookies_with_manual_login(cookie_file_path=cookie_file, dont_store_cookies=dont_store_cookies)
        if cookie is None:
            logging.error("Failed to retrieve cookies with manual login.")
            return None, None, None

    async with API(cookie) as api:
        user_data = await api.validate_cookies()
        if not user_data:
            logging.warning("Cookies are invalid or expired. Attempting to log in manually.")
            cookie = await browser.get_cookies_with_manual_login(cookie_file_path=cookie_file, dont_store_cookies=dont_store_cookies)
            if cookie is not None:
                logging.info("Cookies successfully retrieved with manual login.")
                return await login(cookie=cookie, cookie_file=cookie_file, dont_store_cookies=dont_store_cookies)
        
            logging.error("Failed to retrieve cookies with manual login.")
            return None, None, None

        return user_data, cookie, api.request_data

async def main(
    log_level=logging.INFO,
    cookie: str = None,
    cookie_path: str = "cookies.json.enc",
    dont_store_cookies: bool = False,
    deduplicate_by: int = 1,
    only_show: bool = False,
    execute: bool = False,
    playlist_ids: str = None
):
    logging.basicConfig(level=log_level, format="[%(asctime)s] (%(levelname)s): %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    
    user_data, *api_args = await login(cookie=cookie, cookie_file=cookie_path, dont_store_cookies=dont_store_cookies)
    if not user_data:
        logging.critical("Login failed. Exiting.")
        return
    
    logging.info("Login successful")

    async with API(*api_args) as api:
        playlists = await api.get_playlists()
        if not playlists:
            logging.error("Failed to retrieve playlists.")
            return
        logging.info(f"Retrieved {len(playlists)} playlists")
        
        selected_playlist_nos = []
        if playlist_ids:
            if playlist_ids.upper() == "ALL":
                selected_playlist_nos = list(range(0, len(playlists)))
            else:
                try:
                    selected_playlist_nos = [int(x.strip()) for x in playlist_ids.split(",")]
                    selected_playlist_nos = list(set(selected_playlist_nos))
                    if not all(0 <= x < len(playlists) for x in selected_playlist_nos):
                        logging.warning("Invalid playlist numbers provided via arguments.")
                        return
                except ValueError:
                    logging.warning("Invalid playlist numbers provided via arguments.")
                    return
        else:        
            headers = ["No", "Title", "Songs", "ID"]
            print("\nPlaylists:\n" + tabulate(playlists, headers=headers, tablefmt="rounded_grid"))
            
            while True:
                try:
                    playlist_nos = input("\nWhich playlists do you want to deduplicate? (Enter numbers, seperated by ','. Type 'ALL' for every playlist): ").strip().replace(" ", "")
                    if not playlist_nos:
                        continue
                    if playlist_nos.upper() == "ALL":
                        playlist_nos = list(range(0, len(playlists)))
                    else:
                        playlist_nos = [int(x.strip()) for x in playlist_nos.split(",")]
                        playlist_nos = list(set(playlist_nos)) # remove duplicates
                        if not all(0 < x < len(playlists) for x in playlist_nos):
                            logging.warning("Invalid playlist numbers. Please try again.")
                            continue
                    selected_playlist_nos = playlist_nos
                    break

                except ValueError:
                    logging.warning("Invalid input. Please enter numbers separated by commas.")
                    continue
        
        selected_playlist_titles = ""
        selected_playlist_ids = ""
        for i in selected_playlist_nos:
            selected_playlist_titles += ", " + playlists[i][MV.LIST_INDEX_TITLE]
            selected_playlist_ids += ", " + str(playlists[i][MV.LIST_INDEX_ID])
        logging.info(f"Selected playlists: {selected_playlist_titles[2:]} (IDs: {selected_playlist_ids[2:]})")

        if deduplicate_by:
            dedup_by = deduplicate_by
        else:
            dedup_by = input("\n[1] ISRC\n[2] Song name if it's from the same artist\n[3] Both\n\nDeduplicate by: ").strip()
            while True:
                try:
                    dedup_by = int(dedup_by)
                    if 0 < dedup_by < 4:
                        break
                    
                    logging.warning("Invalid choice. Please enter 1, 2, or 3.")
                    dedup_by = input("Deduplicate by: ").strip()
                    continue
                except ValueError:
                    logging.warning("Invalid choice. Please enter 1, 2, or 3.")
                    return

        if execute and not only_show:
            only_show = False
            logging.info("Really Removing duplicate songs from playlists.")
        elif not execute and not only_show:
            only_show = input("\nOnly show which songs would be removed? (y/n, defaults to yes): ").strip().lower() != "n"
            if only_show:
                logging.info("Only showing which songs would be removed. No changes will be made to playlists.")
            else:
                logging.info("Really Removing duplicate songs from playlists.")
  
        removed_songs = await deduplicate_playlists(
            playlists=[ [playlists[i][MV.LIST_INDEX_TITLE], playlists[i][MV.LIST_INDEX_ID] ] for i in selected_playlist_nos],
            deduplicate_by=dedup_by,
            _api=api,
            only_show=only_show
        )

        for removed_songs_info in removed_songs:
            removed_songs, playlist_name, playlist_id = removed_songs_info
            if removed_songs:
                logging.info(f"Removed {len(removed_songs)} duplicate songs from playlist '{playlist_name}' (ID: {playlist_id})")
                logging.debug(f"Removed songs: {', '.join([song['SNG_TITLE']+song.get('VERSION', '') for song in removed_songs])}")
            else:
                logging.info(f"No duplicate songs found in playlist '{playlist_name}' (ID: {playlist_id})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deezer Playlist Deduplicator")
    parser.add_argument("--log-level", "-ll", nargs="?", default="INFO", help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default is INFO.")
    parser.add_argument("--cookie", "-c", type=str, help="The 'sid' cookie to use for login. If not provided, the script will try to get it from cookies.json.enc. Stores the cookie if -dsc is not present")
    parser.add_argument("--cookie-path", "-cp", type=str, default="cookies.json.enc", help="The path to the cookie file. Default is 'cookies.json.enc'.")
    parser.add_argument("--dont-store-cookies", "-dsc", action="store_true", help="If set, cookies will not be stored to a file.")
    parser.add_argument("--deduplicate-by", "-db", type=int, choices=[1, 2, 3], help="Method to deduplicate by: 1 for ISRC, 2 for song name if it's from the same artist, 3 for both.")
    parser.add_argument("--execute", "-e", "-x", action="store_true", help="If set, the script will execute the deduplication. Otherwise, it will only show which songs would be removed.")
    parser.add_argument("--only-show", "-os", action="store_true", help="If set, the script will only show which songs would be removed. No changes will be made to the playlists. Takes precedence over --execute.")
    parser.add_argument("--playlist-ids", "-pids", type=str, help="Comma-separated IDs of the playlists to deduplicate. If 'ALL', all playlists will be deduplicated.")
    args = parser.parse_args()
    
    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    asyncio.run(main(
        log_level=log_level,
        cookie=args.cookie,
        cookie_path=args.cookie_path,
        dont_store_cookies=args.dont_store_cookies,
        deduplicate_by=args.deduplicate_by,
        execute=args.execute,
        only_show=args.only_show,
        playlist_ids=args.playlist_ids
    ))
