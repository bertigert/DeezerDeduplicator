import asyncio
import logging
import argparse
import re

from tabulate import tabulate

from library.api import API, MV 
from library.util import login, deduplicate_playlists


async def main(
    log_level=logging.INFO,
    cookie: str = None,
    cookie_path: str = "cookies.json.enc",
    dont_store_cookies: bool = False,
    deduplicate_by: int = 1,
    only_show: bool = False,
    execute: bool = False,
    playlist_ids: str = None,
    playlist_names: str = None,
    browser_name: str = "chromium"
):
    logging.basicConfig(level=log_level, format="[%(asctime)s] (%(levelname)s): %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    
    user_data, *api_args = await login(cookie=cookie, cookie_file=cookie_path, dont_store_cookies=dont_store_cookies, browser_name=browser_name)
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
                selected_playlist_ids = {x.strip() for x in playlist_ids.split(",")}
                for i, playlist in enumerate(playlists):
                    if str(playlist[MV.LIST_INDEX_ID]) in selected_playlist_ids:
                        selected_playlist_nos.append(i)
        if playlist_names:
            playlist_names = [name.strip().replace("\\,", ",") for name in re.split(r"(?<!\\),", playlist_names)]
            selected_playlist_names = {x.strip() for x in playlist_names}
            for i, playlist in enumerate(playlists):
                if playlist[MV.LIST_INDEX_TITLE] in selected_playlist_names:
                    selected_playlist_nos.append(i)

        if len(selected_playlist_nos) == 0:      
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
                        if not all(0 <= x < len(playlists) for x in playlist_nos):
                            logging.warning("Invalid playlist numbers. Please try again.")
                            continue
                    selected_playlist_nos = playlist_nos
                    break

                except ValueError:
                    logging.warning("Invalid input. Please enter numbers separated by commas.")
                    continue
        
        selected_playlist_nos = list(set(selected_playlist_nos))  # remove duplicates
        selected_playlist_titles = ""
        selected_playlist_ids = ""
        for i in selected_playlist_nos:
            selected_playlist_titles += ", " + playlists[i][MV.LIST_INDEX_TITLE]
            selected_playlist_ids += ", " + str(playlists[i][MV.LIST_INDEX_ID])
        logging.info(f"Selected playlists: {selected_playlist_titles[2:]} (IDs: {selected_playlist_ids[2:]})")

        if not deduplicate_by:
            deduplicate_by = input("\n[1] ISRC\n[2] Song name if it's from the same artist\n[3] Both\n\nDeduplicate by: ").strip()
            while True:
                try:
                    deduplicate_by = int(deduplicate_by)
                    if 0 < deduplicate_by < 4:
                        break
                    
                    logging.warning("Invalid choice. Please enter 1, 2, or 3.")
                    deduplicate_by = input("Deduplicate by: ").strip()
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
            deduplicate_by=deduplicate_by,
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
    parser.add_argument("--execute", "-e", "-x", action="store_true", help="If set, the script will execute the deduplication.")
    parser.add_argument("--only-show", "-os", action="store_true", help="If set, the script will only show which songs would be removed. No changes will be made to the playlists. Takes precedence over --execute.")
    parser.add_argument("--playlist-ids", "-pids", type=str, help="Comma-separated IDs of the playlists to deduplicate (actual id of the playlist, is in url). If 'ALL', all playlists will be deduplicated.")
    parser.add_argument("--playlist-names", "-pnames", type=str, help="Comma-separated names of the playlists to deduplicate. This is not recommended as duplicate names will lead to both being deduplicated, use --playlist-ids instead. Use \\ to escape commas in names.")
    parser.add_argument("--browser", "-b", type=str, default="chromium", choices=["chromium", "firefox", "webkit"], help="Which Playwright browser to use for login (chromium, firefox, webkit). Default: chromium.")
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
        playlist_ids=args.playlist_ids,
        playlist_names=args.playlist_names,
        browser_name=args.browser.lower()
    ))
