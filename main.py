
import json
import asyncio
from pathlib import Path
import logging
import sys
from tabulate import tabulate

from library.api import API, MV 
import library.browser as browser

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
    deduplicate_by_isrc = deduplicate_by == 1 or deduplicate_by == 3
    deduplicate_by_name = deduplicate_by == 2 or deduplicate_by == 3

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
        song_title = song["SNG_TITLE"] + song["VERSION"] 

        is_song_duplicate = False
        if deduplicate_by_isrc:
            if song["ISRC"] in isrcs:
                duplicates.append(song)
                is_song_duplicate = True
                logging.debug(f"Found duplicate song by ISRC: {song_title} in playlist {playlist[ID]}")
            else:
                isrcs.add(song["ISRC"])
        
        if deduplicate_by_name and not is_song_duplicate:
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
            logging.debug(f"Removed {len(duplicates)} duplicate songs from playlist {playlist[ID]}")
            return duplicates, playlist[NAME], playlist[ID]
        else:
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

async def login(cookies=None) -> tuple[dict, dict, dict] | tuple[None, None, None]:
    """
    Logs in to Deezer using cookies or manual login if cookies are not provided or invalid.
    Args:
        cookies (dict, optional): Cookies to use for login. If None, manual login will be attempted.
    Returns:
        tuple: User data, cookies, and API request data if login is successful, None otherwise.
    """

    if not cookies:
        if not Path("cookies.json").exists():
            logging.info("No cookies found. Please log in manually.")
            cookies = await browser.get_cookies_with_manual_login()
            if cookies:
                logging.error("Failed to retrieve cookies with manual login.")
                return None, None, None
        else: 
            with open("cookies.json", "r") as f:
                cookies = json.load(f)
        
    async with API(cookies) as api:
        user_data = await api.validate_cookies()
        if not user_data:
            logging.warning("Cookies are invalid or expired. Attempting to log in manually.")
            cookies = await browser.get_cookies_with_manual_login()
            if cookies:
                logging.info("Cookies successfully retrieved with manual login.")
                return await login(cookies=cookies)
            else:
                logging.error("Failed to retrieve cookies with manual login.")
                return None, None, None

        return user_data, cookies, api.request_data

async def main(log_level=logging.DEBUG):
    logging.basicConfig(level=log_level, format='[%(asctime)s] (%(levelname)s): %(message)s')
    
    user_data, *api_args = await login()
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
                    break

            except ValueError:
                logging.warning("Invalid input. Please enter numbers separated by commas.")
                continue
        
        logging.info(f"Selected playlists: {', '.join([playlists[i][MV.LIST_INDEX_TITLE] for i in playlist_nos])} (IDs: {', '.join([str(playlists[i][MV.LIST_INDEX_ID]) for i in playlist_nos])})")

        deduplicate_by = input("\n[1] ISRC\n[2] Song name if it's from the same artist\n[3] Both\n\nDeduplicate by: ").strip()
        while True:
            try:
                deduplicate_by = int(deduplicate_by)
                if 0 < deduplicate_by < 4:
                    break
                else:
                    logging.warning("Invalid choice. Please enter 1, 2, or 3.")
                    continue
            except ValueError:
                logging.warning("Invalid choice. Please enter 1, 2, or 3.")
                return
        
        only_show = input("\nOnly show which songs would be removed? (y/n): ").strip().lower() != "n"
        if only_show:
            logging.info("Only showing which songs would be removed. No changes will be made to playlists.")
        else:
            logging.info("Really Removing duplicate songs from playlists.")


        removed_songs = await deduplicate_playlists(
            playlists=[ [playlists[i][MV.LIST_INDEX_TITLE], playlists[i][MV.LIST_INDEX_ID] ] for i in playlist_nos],
            deduplicate_by=deduplicate_by,
            _api=api,
            only_show=only_show
        )

        for removed_songs_info in removed_songs:
            removed_songs, playlist_name, playlist_id = removed_songs_info
            if removed_songs:
                logging.info(f"Removed {len(removed_songs)} duplicate songs from playlist '{playlist_name}' (ID: {playlist_id})")
                logging.debug(f"Removed songs: {', '.join([song['SNG_TITLE']+song["VERSION"] for song in removed_songs])}")
            else:
                logging.info(f"No duplicate songs found in playlist '{playlist_name}' (ID: {playlist_id})")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        log_level = getattr(logging, sys.argv[1].upper(), logging.DEBUG)
        asyncio.run(main(log_level=log_level))
    else:
        asyncio.run(main())
