import logging
import aiohttp

class MV:
    """
    Enum for magic values used in the Deezer API.
    """

    NOT_LOGGED_IN_USER_ID = 0 # user is not logged in
    PLAYLIST_TYPE_USER = "0"
    PLAYLIST_TYPE_FAVORITES = "4"

    LIST_INDEX_INDEX = 0
    LIST_INDEX_TITLE = 1
    LIST_INDEX_AMOUNT_SONGS = 2
    LIST_INDEX_ID = 3

class API:
    """
    Class to interact with the Deezer API asynchronously using aiohttp.
    """

    ENDPOINTS = {
        "user_data": "https://www.deezer.com/ajax/gw-light.php?method=deezer.getUserData&input=3&api_version=1.0&api_token=",
        "get_playlists": "https://www.deezer.com/ajax/gw-light.php?method=deezer.userMenu&input=3&api_version=1.0&api_token=",
        "get_songs_in_playlist": "https://www.deezer.com/ajax/gw-light.php?method=playlist.getSongs&input=3&api_version=1.0&api_token=",
        "delete_songs_from_playlist": "https://www.deezer.com/ajax/gw-light.php?method=playlist.deleteSongs&input=3&api_version=1.0&api_token="
    }

    def __init__(self, cookies, request_data=None):
        self.cookies = cookies
        self.request_data = request_data if request_data else {}
        self.session = None

    async def __aenter__(self):
        await self.create_session()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.session:
            await self.session.close()
            self.session = None
        if exc_type:
            logging.critical(f"An error occurred: {exc_value}")
    

    async def create_session(self):
        """
        Creates an aiohttp session with the provided cookies.
        """
        if not self.session:
            self.session = aiohttp.ClientSession(cookies=self.cookies)

    async def close_session(self):
        """
        Closes the aiohttp session.
        """
        if self.session:
            await self.session.close()
            self.session = None

    async def get_user_data(self) -> dict | None:
        """
        Fetches user data from Deezer API.
        Returns:
            dict: User data if successful, None otherwise.
        """
        if not self.session:
            await self.create_session()
        async with self.session.get(self.ENDPOINTS["user_data"]) as response:
            if response.status == 200:
                resp = await response.json()
                if resp.get("error", []) != []:
                    logging.debug(f"Error fetching user data: {resp['error']}")
                    return None
                
                self.request_data["api_token"] = resp["results"]["checkForm"]
                return resp["results"]
            else:
                logging.debug(f"Failed to fetch user data: {response.status}")
                return None

    async def validate_cookies(self) -> dict | None:
        """
        Validates the cookies by checking if the session can fetch user data.
        Returns:
            dict: User data if cookies are valid, None otherwise.
        """
        user_data = await self.get_user_data()
        if user_data:
            return None if user_data["USER"]["USER_ID"] == MV.NOT_LOGGED_IN_USER_ID else user_data
        return None
    
    async def get_playlists(self) -> list | None:
        """
        Fetches user playlists from Deezer API.
        Returns:
            list: Playlists data if successful, None otherwise.
        """
        if not self.session:
            await self.create_session()

        async with self.session.get(self.ENDPOINTS["get_playlists"]+self.request_data["api_token"]) as response:
            if response.status == 200:
                resp = await response.json()
                if resp.get("error", []) != []:
                    logging.debug(f"Error fetching playlists: {resp['error']}")
                    return None
                
                playlists = [None]
                is_favorites_found = 0
                for i, playlist in enumerate(resp["results"]["PLAYLISTS"]["data"], start=1):
                    if playlist["TYPE"] == MV.PLAYLIST_TYPE_FAVORITES:
                        playlists[0] = [0, playlist["TITLE"], playlist["NB_SONG"], playlist["PLAYLIST_ID"]]
                        is_favorites_found = 1
                    else:
                        playlists.append([
                            i-is_favorites_found,
                            playlist["TITLE"], 
                            playlist["NB_SONG"],
                            playlist["PLAYLIST_ID"]
                        ])
                
                return playlists
            else:
                logging.debug(f"Failed to fetch playlists: {response.status}")
                return None

    async def get_songs_in_playlist(self, playlist_id: int | str) -> list | None:
        """
        Fetches songs in a specific playlist.
        Args:
            playlist_id (int | str): ID of the playlist to fetch songs from.
        Returns:
            list: Songs data if successful, None otherwise.
        """
        if not self.session:
            await self.create_session()
        
        async with self.session.post(
            self.ENDPOINTS["get_songs_in_playlist"]+self.request_data["api_token"], 
            json={
                "playlist_id": str(playlist_id),
                "start": 0,
                "nb": 2000
            }
        ) as response:
            if response.status == 200:
                resp = await response.json()
                if resp.get("error", []) != []:
                    logging.debug(f"Error fetching songs in playlist {playlist_id}: {resp['error']}")
                    return None
                
                return resp["results"]["data"]
            else:
                logging.debug(f"Failed to fetch songs in playlist {playlist_id}: {response.status}")
                return None

    async def remove_songs_from_playlist(self, playlist_id: int | str, song_ids: list[int | str]) -> bool:
        """
        Deletes songs from a specific playlist.
        Args:
            playlist_id (int | str): ID of the playlist to delete songs from.
            song_ids (list[int | str]): List of song IDs to delete.
        Returns:
            bool: True if successful, False otherwise.
        """
        if not self.session:
            await self.create_session()
        
        async with self.session.post(
            self.ENDPOINTS["delete_songs_from_playlist"]+self.request_data["api_token"], 
            json={
                "playlist_id": str(playlist_id),
                "songs": [[int(song_id), 0] for song_id in song_ids],
                "ctxt": {
                    "id": int(playlist_id),
                    "t": "playlist_page"
                }
            }
        ) as response:
            if response.status == 200:
                resp = await response.json()
                if resp.get("error", []) != []:
                    logging.debug(f"Error deleting songs from playlist {playlist_id}: {resp['error']}")
                    return False
                
                return True
            else:
                logging.debug(f"Failed to delete songs from playlist {playlist_id}: {response.status}")
                return False
