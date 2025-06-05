# Deduplicate Deezer Playlists
Deduplicates Playlists and your Favorite Songs from the terminal.

## How It Works
1. Uses playwright to let the user manually log in and gather the login information
    - You need to log in once, the cookies get saved and you only need to login again once they expire
    - Stored cookies are encrypted (encryption file is right there, but should still help)
2. Gathers all playlists
3. Lets the user chose which ones to deduplicate
4. 3 Options to deduplicate
    - By ISRC (unique identifier for songs)
    - By song name if the song is from the same artist
    - Both
5. Can show you which songs to remove without removing them

## Requirements
- Developed in python 3.12, should work for versions below
- playwright
- aiohttp
- tabulate
- cryptography

### Installation:
1. Clone this git
2. Run
    ```
    pip install -r requirements.txt
    ```
3. Possibly run
    ```
    playwright install
    ```
    Follow this [guide](https://playwright.dev/python/docs/intro) for further instructions for playwright.


## Usage
1. Double click `run.bat` or launch it from the terminal (preferred).
2. Follow instructions in the terminal
> For debugging purposes, directly launch the main.py file
