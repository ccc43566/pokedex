import asyncio
import json
from pathlib import Path

import pytest

from pokedex_api.sync.media_dedup import link_alias
from pokedex_api.sync.version_sprites import mirror_versions, save_progress


def test_legacy_urls_keep_their_bytes_but_share_physical_storage(tmp_path: Path) -> None:
    canonical = tmp_path / "canonical.png"
    old_url = tmp_path / "old-name.png"
    canonical.write_bytes(b"identical image bytes")
    old_url.write_bytes(canonical.read_bytes())
    assert not canonical.samefile(old_url)
    assert link_alias(canonical, old_url)
    assert canonical.samefile(old_url)
    assert old_url.read_bytes() == b"identical image bytes"
    assert not link_alias(canonical, old_url)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["canonical.png", "old-name.png"]


def test_invalid_collector_limits_do_not_connect_to_a_database(tmp_path: Path) -> None:
    for options in ({"concurrency": 0}, {"limit": -1}):
        with pytest.raises(ValueError):
            asyncio.run(mirror_versions(
                database_url="unused", media_root=tmp_path, **options,
            ))


def test_progress_checkpoint_is_replaced_with_committed_counts(tmp_path: Path) -> None:
    path = tmp_path / "job" / "progress.json"
    save_progress(str(path), 0, 128, {"downloadedUrls": 0})
    save_progress(str(path), 32, 128, {"downloadedUrls": 31, "failedUrls": 1})
    state = json.loads(path.read_text())
    assert state["processedUrls"] == 32
    assert state["downloadedUrls"] == 31
    assert state["failedUrls"] == 1
    assert list(path.parent.iterdir()) == [path]
