# Deezer Playlist Deduplicator

A simple tool to find and remove duplicate songs from your Deezer playlists and favorites, right from your terminal.

---

## Features

- **Find and remove duplicates** in any playlist or your favorites.
- **Flexible deduplication:** by ISRC (unique song ID), by song name & artist, or both.
- **Preview mode:** See which songs would be removed before making changes.
- **Encrypted cookie storage:** Your login session is stored securely.
- **Works interactively or via command-line arguments.**
- **No Playwright required** if you provide your own Deezer cookie.


## Quick Start

### 1. Download & Install Requirements

You can either:

- **Clone the repository:**
    ```sh
    git clone https://github.com/bertigert/DeezerDeduplicator.git
    cd DeezerDeduplicator
    ```
- **Or [download the ZIP from GitHub](https://github.com/bertigert/DeezMod/archive/refs/heads/main.zip)** and extract it.

Then install dependencies inside the newly created folder:

Note: This was written in python 3.12, older version might work, newer version might require newer versions of the libraries used.

```sh
pip install -r requirements.txt
```

> If you don't want to install Playwright (for headless/CLI-only use), use:
> ```
> pip install -r minrequirements.txt
> ```

### 2. (Optional) Install Playwright Browsers

If you want to log in interactively (using playwright):

```sh
playwright install
```
See [Playwright Python docs](https://playwright.dev/python/docs/intro) for more info.


## Usage

### Interactive Mode

#### On Windows

- Double-click `run.bat`  
  **or**
- Open a terminal and run:
    ```sh
    python main.py
    ```

#### On Linux/macOS

- Run in your terminal:
    ```sh
    bash run.sh
    ```
  or
    ```sh
    python3 main.py
    ```

You'll be guided through login (if needed), playlist selection, and deduplication options.

---

### Command-Line Mode

You can automate everything with arguments:

```sh
python main.py --playlist-ids=ALL --deduplicate-by=3 --execute
```

#### On Windows

You can also use `deduplicate.bat` as an alias for `python main.py`:
```bat
deduplicate --playlist-ids=ALL --deduplicate-by=3 --execute
```

#### On Linux/macOS

You can use `deduplicate.sh`:
```sh
bash deduplicate.sh --playlist-ids=ALL --deduplicate-by=3 --execute
```
> You might want to `chmod +x` the shell files

#### Common Arguments

- `--log-level, -ll`  
  Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO

- `--cookie, -c`  
  Provide your Deezer `sid` cookie directly (no Playwright needed).

- `--cookie-path, -cp`  
  Path to encrypted cookie file. Default: `cookies.json.enc`

- `--dont-store-cookies, -dsc`  
  Don't save cookies to a file.

- `--deduplicate-by, -db`  
  1 = ISRC, 2 = Song name & artist, 3 = Both

- `--execute, -e, -x`  
  Actually remove duplicates

- `--only-show, -os`  
  Only show what would be removed (overrides --execute) If neither --execute or --only-show is set, the user will be prompted.

- `--playlist-ids, -pids`  
  Comma-separated playlist IDs (from Deezer URL), or `ALL` for all playlists.

- `--playlist-names, -pnames`  
  Comma-separated playlist names (not recommended if you have duplicate names). Use `\` to escape commas in names.

- `--browser, -b`  
  Which Playwright browser to use for login (`chromium`, `firefox`, or `webkit`). Default: `chromium`.

#### Example

Preview duplicates in all playlists, using both ISRC and name+artist:

```sh
python main.py --playlist-ids=ALL --deduplicate-by=3 --only-show
```

Actually remove duplicates:

```sh
python main.py --playlist-ids=ALL --deduplicate-by=3 --execute
```

## FAQ

**Q: Do I need Playwright?**  
A: Only if you want to log in interactively. If you provide a valid `sid` cookie (via `--cookie` or `--cookie-path`), Playwright is not needed.

**Q: How do I get my Deezer `sid` cookie?**  
A: Use browser dev tools or an extension to copy the `sid` cookie after logging in to Deezer.

**Q: Is my login info safe?**  
A: Your cookie is encrypted on disk using a key in the repo. You can manually edit the key, but it really wouldn't change anything.


## Troubleshooting

- If you get errors about Playwright, make sure it's installed and run `playwright install`.
- If login fails, try deleting `cookies.json.enc` and logging in again.
- For more details, run with `--log-level DEBUG`.
