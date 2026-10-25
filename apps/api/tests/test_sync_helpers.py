import httpx
import pytest

from pokedex_api.sync.importer import (
    clean_text,
    localized_entries,
    localized_names,
    nested_value,
    resource_id_from_url,
)
from pokedex_api.sync.provider import PokeApiProvider


def test_resource_id_from_url() -> None:
    assert resource_id_from_url("https://pokeapi.co/api/v2/pokemon/25/") == 25


def test_clean_text_removes_form_feed_and_collapses_whitespace() -> None:
    assert clean_text("hello\f world\n\nagain") == "hello world again"


def test_localized_names_keeps_supported_locales() -> None:
    payload = {
        "names": [
            {"name": "皮卡丘", "language": {"name": "zh-Hans"}},
            {"name": "Pikachu", "language": {"name": "en"}},
            {"name": "ピカチュウ", "language": {"name": "ja"}},
        ]
    }
    assert localized_names(payload) == [("zh-Hans", "皮卡丘"), ("en", "Pikachu")]


def test_localized_entries_reads_version_and_text_field() -> None:
    payload = {
        "flavor_text_entries": [
            {
                "flavor_text": "A mouse-like Pokemon.",
                "language": {"name": "en"},
                "version": {"name": "red"},
            }
        ]
    }
    assert localized_entries(
        payload,
        "flavor_text_entries",
        text_field="flavor_text",
        version_field="version",
    ) == [("en", "red", "A mouse-like Pokemon.")]


def test_nested_value_handles_missing_paths() -> None:
    assert nested_value(
        {"other": {"home": {"front_default": "x"}}},
        ("other", "home", "front_default"),
    ) == "x"
    assert nested_value({"other": None}, ("other", "home", "front_default")) is None


@pytest.mark.asyncio
async def test_provider_keeps_api_v2_base_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.test/api/v2/meta/"
        return httpx.Response(200, json={"hash": "abc"})

    transport = httpx.MockTransport(handler)
    provider = PokeApiProvider("https://example.test/api/v2", "test-agent")
    await provider._client.aclose()
    provider._client = httpx.AsyncClient(transport=transport)
    try:
        assert await provider.get_meta() == {"hash": "abc"}
    finally:
        await provider.aclose()
