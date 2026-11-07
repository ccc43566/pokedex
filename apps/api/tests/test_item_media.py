import asyncio
import hashlib
from pathlib import Path

import pytest
from PIL import UnidentifiedImageError

from pokedex_api.sync.item_media import collect, shared_path, store_content


def test_shared_content_keeps_original_media_and_reuses_one_file(tmp_path: Path) -> None:
    # Make a valid 1x1 PNG through Pillow: fixture validity is part of the downloader contract.
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGBA", (1, 1), (255, 0, 0, 255)).save(buf, format="PNG")
    data = buf.getvalue()
    old = tmp_path / "existing-pokemon.png"
    old.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    existing = {digest: old.name}
    assert store_content(tmp_path, data, existing) == (digest, old.name, False)
    assert old.read_bytes() == data and len(list(tmp_path.rglob("*.png"))) == 1


def test_new_content_is_sha256_named_and_idempotent(tmp_path: Path) -> None:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (2, 2), "blue").save(buf, format="PNG")
    data = buf.getvalue()
    existing = {}
    digest, path, created = store_content(tmp_path, data, existing)
    assert created and digest in path
    assert store_content(tmp_path, data, existing) == (digest, path, False)
    assert len(list(tmp_path.rglob("*.png"))) == 1


def test_wrong_hash_or_path_never_overwrites_existing_file(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        shared_path(tmp_path, "../wrong.png")
    with pytest.raises(UnidentifiedImageError):
        store_content(tmp_path, b"not an image", {})


def test_invalid_limits_do_not_connect_or_mutate(tmp_path: Path) -> None:
    for options in ({"limit": -1}, {"concurrency": 0}, {"concurrency": 13}):
        with pytest.raises(ValueError):
            asyncio.run(collect(database_url="unused", media_root=tmp_path, **options))
    assert not list(tmp_path.iterdir())
