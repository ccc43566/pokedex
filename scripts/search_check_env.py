"""Run a command against the disposable search verification database only."""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import URL, make_url

root = Path(__file__).resolve().parents[1]
config = dotenv_values(root / ".env")
url = (
    make_url(config["DATABASE_URL"])
    if config.get("DATABASE_URL")
    else URL.create(
        "postgresql+asyncpg",
        username=config.get("POSTGRES_USER", "pokedex"),
        password=config.get("POSTGRES_PASSWORD", "pokedex"),
        host="127.0.0.1",
        database="pokedex",
    )
)
url = url.set(host="127.0.0.1", port=15432, database="pokedex_search_check")
env = {
    **os.environ,
    "DATABASE_URL": url.render_as_string(hide_password=False),
    "MEDIA_ROOT": str(root / "apps/api/data/search-check-media"),
}
sys.exit(
    subprocess.call([sys.executable, *sys.argv[1:]], cwd=root / "apps/api", env=env)
)
