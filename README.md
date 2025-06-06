# Deduplicate Deezer Playlists
Deduplicates Playlists and your Favorite Songs from the terminal.

## How It Works
1. Uses playwright to let the user manually log in and gather the login information, if the user does not provide any form of cookie,
    - You need to log in once, the cookies get saved and you only need to login again once they expire
    - Stored cookies are encrypted
2. Gathers all playlists
3. Lets the user chose which ones to deduplicate
4. 3 options to deduplicate
    - By ISRC (unique identifier for songs)
    - By song name if the song is from the same artist
    - Both
5. Can show you which songs to remove without removing them

## Requirements
Developed in python 3.12, should work for versions below

Python Modules:
- playwright (optional, see Usage)
- aiohttp
- tabulate
- cryptography

> In detail: aiohttp, aiosignal,attrs, cffi, cryptography, frozenlist, greenlet, idna, multidict, playwright, propcache, pycparser, pyee, tabulate, typing_extensions, yarl

## Installation:
1. Clone this git
2. Run
    ```
    pip install -r requirements.txt
    ```
    or to avoid installing playwright
    ```
    pip install -r minrequirements.txt
    ```
3. Possibly run
    ```
    playwright install
    ```
    Follow this [guide](https://playwright.dev/python/docs/intro) for further instructions for playwright.


## Usage

### Option 1 (Interactive)
1. Double click `run.bat` or launch it from the terminal (preferred) for interactive usage.
2. Follow instructions in the terminal

### Option 2 (CLI)
Run directly from the shell using arguments.

#### Important Note: 

If you provide a valid cookie through either of the following options
- an encrypted json file containing the 'sid' valid cookie, probably created by this script (--cookie-path)
- the valid value of the 'sid' cookie as a string argument (--cookie)

then you **don't** need to have the `playwright` module installed, allowing for use in a terminal only environment (tested on termux on android with python 3.11.8). Use DevTools or an extension to get it. Since it is a secure cookie, there really is no legit automated way to get it.

The 'sid' cookie looks something like this `fr5134c3g321d3c50c14f57ab5d33314b75d4eff`

#### Arguments

```
$ py .\main.py --help
usage: main.py [-h] [--log-level [LOG_LEVEL]] [--cookie COOKIE] [--cookie-path COOKIE_PATH] [--dont-store-cookies] [--deduplicate-by {1,2,3}] [--execute] [--only-show] [--playlist-ids PLAYLIST_IDS]
               [--playlist-names PLAYLIST_NAMES]

Deezer Playlist Deduplicator

options:
  -h, --help            show this help message and exit
  --log-level [LOG_LEVEL], -ll [LOG_LEVEL]
                        Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default is INFO.
  --cookie COOKIE, -c COOKIE
                        The 'sid' cookie to use for login. If not provided, the script will try to get it from cookies.json.enc. Stores the cookie if -dsc is not present
  --cookie-path COOKIE_PATH, -cp COOKIE_PATH
                        The path to the cookie file. Default is 'cookies.json.enc'.
  --dont-store-cookies, -dsc
                        If set, cookies will not be stored to a file.
  --deduplicate-by {1,2,3}, -db {1,2,3}
                        Method to deduplicate by: 1 for ISRC, 2 for song name if it's from the same artist, 3 for both.
  --execute, -e, -x     If set, the script will execute the deduplication. Otherwise, it will only show which songs would be removed.
  --only-show, -os      If set, the script will only show which songs would be removed. No changes will be made to the playlists. Takes precedence over --execute.
  --playlist-ids PLAYLIST_IDS, -pids PLAYLIST_IDS
                        Comma-separated IDs of the playlists to deduplicate (actual id of the playlist, is in url). If 'ALL', all playlists will be deduplicated.
  --playlist-names PLAYLIST_NAMES, -pnames PLAYLIST_NAMES
                        Comma-separated names of the playlists to deduplicate. If 'ALL', all playlists will be deduplicated. This is not recommended as duplicate names will lead to both being
                        deduplicated, use --playlist-ids instead. Use \ to escape commas in names.
```

#### Examples:
`python main.py -pids=ALL -db=3 -ll=INFO -os`
Checks for duplicate songs by ISRC and by name in every playlist.