# wikitui

Terminal browser for a [BookStack](https://www.bookstackapp.com/) wiki with Markdown
rendering, built on Textual. Point it at your instance with `WIKI_URL` or the config
file below (the built-in default is the placeholder `https://wiki.example.com`).

![wikitui demo](docs/demo.gif)

## Setup

```
uv sync
```

Create an API token in BookStack (*Edit Profile → API Tokens*) and either export

```
export WIKI_TOKEN_ID=...
export WIKI_TOKEN_SECRET=...
```

or write `~/.config/wikitui/config.toml`:

```toml
url = "https://wiki.example.com"
token_id = "..."
token_secret = "..."
```

## Run

```
uv run wikitui
```

## Standalone binary

Build a single-file executable (PyInstaller, Linux x86_64) with:

```
./build.sh
```

The result is `dist/wikitui`; copy it anywhere on your `PATH`. It reads the same
token env vars / config file as above. `dist/` is not committed.

## Keys

| Key | Action |
| --- | --- |
| `↑/↓/Enter` | navigate tree, open page |
| `←/→` | previous / next page in the current book |
| `/` | search |
| `b` | toggle sidebar |
| `r` | reload books |
| `o` | open current page in browser |
| `q` | quit |

Pages written in Markdown are shown as-is; HTML pages are converted to Markdown.
Links to other wiki pages open in the viewer; external links open in your browser.
