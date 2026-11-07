from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import LocalizedName, SourceRecord
from pokedex_api.services.evolution_conditions import (
    ConditionContext,
    explain_expression,
    explain_method,
    load_condition_context,
    parse_rpn,
    policy,
)

DATA = json.loads(
    (Path(__file__).parent / "fixtures/evolution-conditions.json").read_text(encoding="utf-8")
)


@pytest.fixture
def context() -> ConditionContext:
    context = ConditionContext()
    for row in DATA["dictionaries"]:
        key = (row["resource_type"], row["resource_id"])
        context.sources[key] = dict(
            raw_payload=copy.deepcopy(row["payload"]),
            source_url=f"https://pokeapi.co/api/v2/{key[0]}/{key[1]}/",
            source_hash="a" * 64,
        )
    context.names[("move", 887)] = ("强力钻", "upstream-translation")
    context.names[("item", 1167)] = ("草莓糖饰", "upstream-translation")
    return context


def interpreted(row: dict[str, Any], context: ConditionContext):
    def sid(r: dict[str, Any]) -> int:
        return int(r["url"].rstrip("/").split("/")[-1])

    return explain_method(
        row["method"],
        context,
        source_species_id=sid(row["source"]),
        target_species_id=sid(row["target"]),
    )


def test_nincada_edges_and_independent_supplement(context: ConditionContext) -> None:
    rows = [r for r in DATA["methods"] if r["source"]["name"] == "nincada"]
    ninja = interpreted(next(r for r in rows if r["target"]["name"] == "ninjask"), context)
    shell = interpreted(next(r for r in rows if r["target"]["name"] == "shedinja"), context)
    assert ninja.conditions == ["等级达到 20 后升级进化"]
    assert not ninja.supplements
    assert shell.conditions == ["土居忍士进化为铁面忍者时，蜕壳产生的额外宝可梦"]
    assert shell.supplements[0]["raw_pokeapi_fields"] is False
    assert shell.supplements[0]["scope"][0]["version_group_ids"] == [5, 6, 7]
    assert "不需要额外" in shell.supplements[0]["scope"][0]["zh"]
    assert "消耗" in shell.supplements[0]["scope"][1]["zh"]


@pytest.mark.parametrize(
    "row", [r for r in DATA["methods"] if r["method"].get("condition_expression")]
)
def test_all_real_expression_methods(row: dict[str, Any], context: ConditionContext) -> None:
    before = copy.deepcopy(row["method"])
    result = interpreted(row, context)
    assert row["method"] == before
    assert not result.unresolved
    expression = before["condition_expression"]
    text = "；".join(result.conditions)
    assert expression["expression"] not in text
    if expression["percentage_chance"] is not None:
        assert f"{expression['percentage_chance']}%" in text
        assert "由个体内部值决定" in text
    else:
        assert "%" not in text
        assert "旋转" in text and "时间：" in text and "携带道具：" in text


def test_branch_labels_versions_and_other_conditions(context: ConditionContext) -> None:
    rows = [
        r for r in DATA["methods"] if r["source"]["name"] in {"dunsparce", "tandemaus", "wurmple"}
    ]
    for row in rows:
        result = interpreted(row, context)
        assert result.version_group == row["method"]["version_group"]
        assert result.is_default == row["method"]["is_default"]
        if row["source"]["name"] == "dunsparce":
            assert any("强力钻" in c for c in result.conditions)
        elif row["source"]["name"] == "tandemaus":
            assert any("25" in c and "对战" in c for c in result.conditions)
        else:
            assert "等级达到 7 后升级进化" in result.conditions
    assert {
        r["method"]["version_group"]["name"] for r in rows if r["source"]["name"] == "wurmple"
    } == {"ruby-sapphire", "x-y"}


def test_spin_mapping_requires_verified_definition_and_units(context: ConditionContext) -> None:
    expression = dict(
        expression="SPIN_DIR 0 == SPIN_SEC 5 < &&",
        percentage_chance=None,
        variables=[
            dict(url="https://pokeapi.co/api/v2/evolution-variable/3/"),
            dict(url="https://pokeapi.co/api/v2/evolution-variable/4/"),
        ],
    )
    lines, _, issues, _ = explain_expression(expression, context, None)
    assert not issues and lines == ["顺时针旋转", "旋转持续少于 5 秒"]
    other = copy.deepcopy(expression)
    other["expression"] = "SPIN_DIR 1 == SPIN_SEC 5 >= &&"
    assert explain_expression(other, context, None)[0] == ["逆时针旋转", "旋转持续至少 5 秒"]
    context.sources[("evolution-variable", 3)]["raw_payload"]["descriptions"] = []
    assert explain_expression(expression, context, None)[0] == ["特殊条件待解释"]


@pytest.mark.parametrize(
    "expression",
    ["EC 100 % 0 ==", "EC 99 % 0 ==", '__import__("os")', "EC 0 == ||", "EC 0 1", "X 100 % 0 =="],
)
def test_unknown_formula_no_invented_probability(
    expression: str, context: ConditionContext
) -> None:
    value = dict(
        expression=expression,
        percentage_chance=None,
        variables=[dict(url="https://pokeapi.co/api/v2/evolution-variable/1/")],
    )
    lines, _, issues, _ = explain_expression(value, context, None)
    assert not any("99%" in line or "1%" in line for line in lines)
    if expression != "EC 100 % 0 ==":
        assert issues and "特殊条件待解释" in lines


def test_unknown_formula_keeps_source_percentage_without_guessing(
    context: ConditionContext,
) -> None:
    value = dict(
        expression="EC 9 +",
        percentage_chance=7,
        variables=[dict(url="https://pokeapi.co/api/v2/evolution-variable/1/")],
    )
    lines, _, issues, _ = explain_expression(value, context, None)
    assert issues and "特殊条件待解释" in lines
    assert any("7%" in line for line in lines)
    assert not any("由个体内部值决定" in line for line in lines)
    with pytest.raises(ValueError):
        parse_rpn("1 " * 1000, set())


async def test_upstream_chinese_separate_from_project_and_english_fallback(
    session: AsyncSession,
) -> None:
    session.add_all(
        [
            LocalizedName(
                entity_type="evolution-trigger", entity_id=1, locale="zh-Hans", name="上游中文"
            ),
            LocalizedName(entity_type="move", entity_id=887, locale="en", name="Hyper Drill"),
            SourceRecord(
                resource_type="evolution-trigger",
                resource_id=1,
                source_url="https://example.test/1/",
                source_hash="b" * 64,
                raw_payload=dict(id=1, name="level-up"),
            ),
        ]
    )
    await session.commit()
    method = dict(
        trigger=dict(name="level-up", url="https://pokeapi.co/api/v2/evolution-trigger/1/"),
        min_level=32,
        known_move=dict(name="hyper-drill", url="https://pokeapi.co/api/v2/move/887/"),
        is_default=False,
    )
    context = await load_condition_context(session, [method], "zh-Hans")
    result = explain_method(method, context, source_species_id=206, target_species_id=982)
    assert (
        result.trigger_label == "上游中文" and result.trigger_name_origin == "upstream-translation"
    )
    assert "学会招式：Hyper Drill" in result.conditions
    assert result.is_default is False and result.sources[0].kind == "project-explanation"
    assert (await session.get(SourceRecord, 1)).raw_payload == dict(id=1, name="level-up")


def test_extra_fields_zero_false_and_trade_do_not_lose_conditions(
    context: ConditionContext,
) -> None:
    method = dict(
        trigger=dict(name="trade"),
        held_item=dict(name="metal-coat"),
        relative_physical_stats=0,
        gender=1,
        min_happiness=0,
        version_group=dict(name="gold-silver"),
        unknown_flag=False,
        is_default=False,
        condition_expression=dict(expression="not-known", variables=[]),
    )
    result = explain_method(method, context, source_species_id=95, target_species_id=208)
    assert "攻击 = 防御" in result.conditions and "亲密度至少：0" in result.conditions
    assert "性别：雌性" in result.conditions and any("metal coat" in c for c in result.conditions)
    assert any("unknown_flag" in c for c in result.conditions)
    assert result.status == "partial" and result.version_group == method["version_group"]
    assert result.trigger_label == policy()["triggers"]["trade"]
    assert any("不表示所有游戏" in n for n in result.notes)
