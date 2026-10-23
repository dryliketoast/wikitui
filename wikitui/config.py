import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "wikitui" / "config.toml"
DEFAULT_URL = "https://wiki.example.com"


@dataclass
class Config:
    url: str = DEFAULT_URL
    token_id: str = ""
    token_secret: str = ""

    @property
    def auth_header(self) -> dict[str, str]:
        if self.token_id and self.token_secret:
            return {"Authorization": f"Token {self.token_id}:{self.token_secret}"}
        return {}


def load_config() -> Config:
    """Load settings from the config file, with WIKI_* env vars taking priority."""
    data: dict = {}
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("rb") as f:
            data = tomllib.load(f)
    return Config(
        url=(os.environ.get("WIKI_URL") or data.get("url") or DEFAULT_URL).rstrip("/"),
        token_id=os.environ.get("WIKI_TOKEN_ID") or data.get("token_id", ""),
        token_secret=os.environ.get("WIKI_TOKEN_SECRET") or data.get("token_secret", ""),
    )
