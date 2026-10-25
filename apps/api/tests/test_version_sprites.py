import asyncio
from io import BytesIO

import httpx
from PIL import Image
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from pokedex_api.models import Base, Pokemon, PokemonForm, VersionSprite
from pokedex_api.services.version_sprites import get_version_media
from pokedex_api.sync.version_sprites import download_one, sprite_rows, validate_image


def test_source_fields_keep_null_and_game_identity() -> None:
    rows = list(
        sprite_rows(
            "pokemon",
            1,
            {
                "versions": {
                    "generation-i": {
                        "red-blue": {
                            "front_default": "https://example.test/1.png",
                            "front_female": None,
                        }
                    },
                    "generation-v": {
                        "black-white": {"animated": {"front_default": "https://example.test/1.gif"}}
                    },
                }
            },
        )
    )
    assert [(row[2], row[3], row[4], row[7]) for row in rows] == [
        ("generation-i", "red-blue", "front_default", "pending"),
        ("generation-i", "red-blue", "front_female", "null"),
        ("generation-v", "black-white", "animated/front_default", "pending"),
    ]
    assert rows[-1][6] == "gif"


def test_gif_animation_is_validated_without_conversion() -> None:
    output = BytesIO()
    images = [Image.new("RGBA", (2, 2), color) for color in ("red", "blue")]
    images[0].save(output, format="GIF", save_all=True, append_images=images[1:], duration=100)
    data = output.getvalue()
    assert data.startswith(b"GIF")
    assert validate_image(data, "gif") == (2, 2, 2)


def test_failed_and_corrupt_downloads_are_distinct() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/missing.png":
            return httpx.Response(404)
        return httpx.Response(200, content=b"not an image")

    async def check() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            semaphore = asyncio.Semaphore(1)
            failure = await download_one(
                client, semaphore, "https://example.test/missing.png", "png"
            )
            corrupt = await download_one(
                client, semaphore, "https://example.test/broken.png", "png"
            )
            assert failure[0] == "download_failed"
            assert corrupt[0] == "corrupt"

    asyncio.run(check())


def test_version_media_includes_form_and_null_without_remote_fallback() -> None:
    async def check() -> None:
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            session.add(Pokemon(id=1, name="bulbasaur", sprites={}, raw_payload={}))
            session.add(
                PokemonForm(id=1, name="bulbasaur-form", pokemon_id=1, sprites={}, raw_payload={})
            )
            session.add(
                VersionSprite(
                    owner_type="pokemon",
                    owner_id=1,
                    generation="generation-i",
                    game="red-blue",
                    kind="front_default",
                    status="downloaded",
                    source_url="https://example.test/front.png",
                    local_path="version-sprites/aa/hash.png",
                    format="png",
                    checksum="hash",
                    byte_size=123,
                    width=32,
                    height=32,
                )
            )
            session.add(
                VersionSprite(
                    owner_type="form",
                    owner_id=1,
                    generation="generation-i",
                    game="red-blue",
                    kind="front_female",
                    status="null",
                )
            )
            await session.commit()
            result = await get_version_media(session, "1")
            assert result is not None
            assert len(result.owners) == 2
            assert len(result.sprites) == 2
            downloaded = next(row for row in result.sprites if row.status == "downloaded")
            missing = next(row for row in result.sprites if row.status == "null")
            assert downloaded.url == "/media/version-sprites/aa/hash.png"
            assert missing.url is None
        await engine.dispose()

    asyncio.run(check())
