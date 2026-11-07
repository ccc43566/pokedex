"""Explain, never execute, preserved evolution conditions and a bounded RPN grammar."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pokedex_api.models import LocalizedName, SourceRecord
from pokedex_api.schemas import EvolutionConditionSource, EvolutionMethodExplanation

POLICY_PATH = Path(__file__).resolve().parents[1] / "data/evolution_explanations.json"


@lru_cache(maxsize=1)
def policy() -> dict[str, Any]:
    with POLICY_PATH.open(encoding="utf-8") as source:
        return dict(json.load(source))


def policy_hash() -> str:
    return hashlib.sha256(
        json.dumps(policy(), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def ref_key(value: Any) -> tuple[str, int] | None:
    if not isinstance(value, dict):
        return None
    parts = str(value.get("url", "")).rstrip("/").split("/")
    if len(parts) >= 2 and parts[-1].removeprefix("-").isdigit():
        return parts[-2], int(parts[-1])
    return None


def refs(value: Any) -> set[tuple[str, int]]:
    if isinstance(value, dict):
        key = ref_key(value)
        return {key} if key else set().union(*(refs(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(refs(v) for v in value))
    return set()


@dataclass
class ConditionContext:
    locale: str = "zh-Hans"
    names: dict[tuple[str, int], tuple[str, str]] = field(default_factory=dict)
    sources: dict[tuple[str, int], dict[str, Any]] = field(default_factory=dict)

    @property
    def zh(self) -> bool:
        return self.locale == "zh-Hans"

    def text(self, zh: str, en: str) -> str:
        return zh if self.zh else en

    def name(self, value: Any) -> str:
        key = ref_key(value)
        if key in self.names:
            return self.names[key][0]
        if isinstance(value, dict):
            return str(value.get("name") or value.get("url") or "?").replace("-", " ")
        return str(value)

    def version_name(self, value: Any) -> str:
        key = ref_key(value)
        source = self.sources.get(key or ("", 0), {}).get("raw_payload", {})
        versions = source.get("versions") or []
        return "／".join(self.name(v) for v in versions) if versions else self.name(value)

    def evidence(self, value: Any) -> dict[str, Any] | None:
        return self.sources.get(ref_key(value) or ("", 0))


async def load_condition_context(
    session: AsyncSession, methods: list[dict[str, Any]], locale: str
) -> ConditionContext:
    context = ConditionContext(locale=locale)
    wanted = refs(methods)
    sources = (
        await session.scalars(
            select(SourceRecord).where(
                SourceRecord.resource_type.in_(
                    ["evolution-trigger", "evolution-variable", "version-group", "version"]
                )
            )
        )
    ).all()
    for source in sources:
        key = (source.resource_type, source.resource_id)
        context.sources[key] = dict(
            resource_type=source.resource_type,
            resource_id=source.resource_id,
            source_url=source.source_url,
            source_hash=source.source_hash,
            fetched_at=source.fetched_at.isoformat(),
            raw_payload=source.raw_payload,
        )
        if source.resource_type in {"version", "version-group"}:
            wanted.add(key)
    if wanted:
        names = (
            await session.scalars(
                select(LocalizedName)
                .where(
                    LocalizedName.entity_type.in_({k[0] for k in wanted}),
                    LocalizedName.entity_id.in_({k[1] for k in wanted}),
                    LocalizedName.locale.in_([locale, "en"]),
                )
                .order_by(LocalizedName.id)
            )
        ).all()
        for language in dict.fromkeys([locale, "en"]):
            for name in names:
                key = (name.entity_type, name.entity_id)
                if name.locale == language and key in wanted and key not in context.names:
                    context.names[key] = (
                        name.name,
                        "upstream-translation" if language == locale else "upstream-english",
                    )
    return context


def parse_rpn(expression: str, symbols: set[str]) -> Any:
    """Build a bounded syntax tree only. No eval/exec, function calls or numeric evaluation."""
    tokens = expression.split()
    if not tokens or len(tokens) > 96 or len(expression) > 1024:
        raise ValueError("Expression exceeds supported bounds")
    stack: list[Any] = []
    for token in tokens:
        if token in {"%", ">>", "==", "!=", "<", ">", "<=", ">=", "&&", "||"}:
            if len(stack) < 2:
                raise ValueError("Incomplete RPN operands")
            right, left = stack.pop(), stack.pop()
            stack.append((token, left, right))
        elif token in symbols or (len(token) <= 16 and re.fullmatch(r"-?\d+(?:\.\d+)?", token)):
            stack.append(token)
        else:
            raise ValueError("Unknown token or undeclared variable")
    if len(stack) != 1:
        raise ValueError("RPN has extra operands")
    return stack[0]


def explain_expression(
    condition: dict[str, Any], context: ConditionContext, target_form: Any
) -> tuple[list[str], list[str], list[str], list[dict[str, Any]]]:
    lines: list[str] = []
    notes: list[str] = []
    issues: list[str] = []
    evidence: list[dict[str, Any]] = []
    validated: dict[str, dict[str, Any]] = {}
    if not isinstance(condition, dict):
        return (
            [context.text("特殊条件待解释", "Special condition awaiting explanation")],
            [],
            ["Malformed condition_expression"],
            [],
        )
    expression = condition.get("expression")
    percentage = condition.get("percentage_chance")
    valid_percentage = (
        isinstance(percentage, (int, float))
        and not isinstance(percentage, bool)
        and 0 <= percentage <= 100
        and math.isfinite(percentage)
    )
    for variable in condition.get("variables") or []:
        source = context.evidence(variable)
        if source:
            evidence.append(source)
        raw = (source or {}).get("raw_payload", {})
        spec = policy()["variables"].get(raw.get("name"))
        descriptions = " ".join(
            v.get("description", "")
            for v in raw.get("descriptions", [])
            if v.get("language", {}).get("name") == "en"
        ).lower()
        if (
            not spec
            or any(raw.get(k) != spec[k] for k in ("symbol", "source", "data_type"))
            or any(s not in descriptions for s in spec["description_requirements"])
        ):
            issues.append("Variable definition missing or incompatible")
        else:
            validated[raw["symbol"]] = spec
    try:
        if issues or not isinstance(expression, str):
            raise ValueError("Variable definitions cannot be verified")
        tree = parse_rpn(expression, set(validated))
        internal = False
        if isinstance(tree, tuple) and tree[0] in {"==", "!=", "<=", ">="}:
            op, left, right = tree
            if (
                isinstance(left, tuple)
                and left[0] == "%"
                and left[2] == "100"
                and right == "0"
                and op in {"==", "!="}
                and isinstance(left[1], str)
                and validated.get(left[1], {}).get("role") == "internal"
            ):
                internal = True
            elif (
                isinstance(left, tuple)
                and left[0] == "%"
                and left[2] == "10"
                and isinstance(left[1], tuple)
                and left[1][0] == ">>"
                and left[1][2] == "16"
                and validated.get(left[1][1], {}).get("role") == "internal"
                and (op, right) in {("<=", "4"), (">=", "5")}
            ):
                internal = True
        if internal:
            branch = policy()["branch_labels"].get((target_form or {}).get("name"), "")
            prefix = (
                f"{branch}："
                if context.zh and branch
                else context.text("该分支：", "This branch: ")
            )
            if valid_percentage:
                lines.append(
                    prefix
                    + context.text(
                        f"约 {percentage:g}%（由个体内部值决定）",
                        f"about {percentage:g}% "
                        "(determined by the Pokémon's stored internal value)",
                    )
                )
            else:
                lines.append(
                    prefix
                    + context.text(
                        "由个体内部值决定；来源未提供分支比例",
                        "determined by a stored internal value; no percentage provided",
                    )
                )
            notes.append(
                context.text(
                    "比例来自本条数据源记录；并非每次进化重新抽取概率，"
                    "且不承诺覆盖所有版本或特殊情况。",
                    "The percentage is the value in this record, not a fresh random roll at each "
                    "evolution; it does not cover every version or special case.",
                )
            )
        else:
            clauses: list[Any] = []

            def flatten(node: Any) -> None:
                if isinstance(node, tuple) and node[0] == "&&":
                    flatten(node[1])
                    flatten(node[2])
                else:
                    clauses.append(node)

            flatten(tree)
            spin_lines = []
            for clause in clauses:
                if not isinstance(clause, tuple):
                    raise ValueError("Unsupported condition expression")
                op, symbol, value = clause
                spec = validated.get(symbol) if isinstance(symbol, str) else None
                if not spec or not isinstance(value, str):
                    raise ValueError("Unsupported condition expression")
                if spec["role"] == "direction" and op == "==" and value in spec["values"]:
                    direction = spec["values"][value]["zh" if context.zh else "en"]
                    spin_lines.append(context.text(f"{direction}旋转", f"Spin {direction}"))
                elif (
                    spec["role"] == "duration"
                    and op in {"<", "<=", ">", ">=", "=="}
                    and re.fullmatch(r"\d+(?:\.\d+)?", value)
                    and float(value) <= 255
                ):
                    zh_op = {"<": "少于", "<=": "不超过", ">": "超过", ">=": "至少", "==": "等于"}[
                        op
                    ]
                    en_op = {
                        "<": "less than",
                        "<=": "at most",
                        ">": "more than",
                        ">=": "at least",
                        "==": "exactly",
                    }[op]
                    spin_lines.append(
                        context.text(
                            f"旋转持续{zh_op} {value} 秒", f"Spin for {en_op} {value} seconds"
                        )
                    )
                else:
                    raise ValueError("Unsupported condition expression")
            if not spin_lines or valid_percentage:
                raise ValueError("Unsupported or conflicting spin expression")
            lines.extend(spin_lines)
    except (ValueError, TypeError, KeyError):
        issues.append("Unsupported condition expression or unverifiable variable semantics")
        lines = [context.text("特殊条件待解释", "Special condition awaiting explanation")]
        if valid_percentage:
            lines.append(
                context.text(
                    f"数据源标注比例约 {percentage:g}%；不据此推断公式含义",
                    f"Source percentage: about {percentage:g}%; "
                    "expression semantics are not inferred",
                )
            )
    if percentage is not None and not valid_percentage:
        issues.append("Invalid percentage_chance")
    return lines, notes, list(dict.fromkeys(issues)), evidence


def explain_method(
    method: dict[str, Any],
    context: ConditionContext,
    *,
    source_species_id: int,
    target_species_id: int,
    source_label: str = "",
    target_label: str = "",
) -> EvolutionMethodExplanation:
    p = policy()
    trigger = method.get("trigger") or {}
    slug = trigger.get("name", "")
    trigger_key = ref_key(trigger)
    original_name = context.names.get(trigger_key or ("", 0))
    if context.zh and original_name and original_name[1] == "upstream-translation":
        label, origin = original_name
    elif context.zh and slug in p["triggers"]:
        label, origin = p["triggers"][slug], "project-glossary"
    else:
        label, origin = original_name or (context.name(trigger), "identifier")
    result = EvolutionMethodExplanation(
        rule_version=p["version"],
        trigger_label=label,
        trigger_name_origin=origin,
        version_group=method.get("version_group"),
        is_default=method.get("is_default"),
    )
    result.sources.append(
        EvolutionConditionSource(
            kind="project-explanation",
            label=context.text(
                "项目释义（独立于上游原文）", "Project explanation (separate from upstream text)"
            ),
            url=p["source_url"],
            content_hash=policy_hash(),
        )
    )
    result.sources.append(
        EvolutionConditionSource(
            kind="upstream", label="PokéAPI", url="https://pokeapi.co/docs/v2/#evolution-section"
        )
    )
    trigger_source = context.evidence(trigger)
    if trigger_source:
        result.sources.append(
            EvolutionConditionSource(
                kind="upstream",
                label=context.name(trigger),
                url=trigger_source["source_url"],
                content_hash=trigger_source["source_hash"],
            )
        )
    level = method.get("min_level")
    handled = {"trigger", "min_level", "version_group", "is_default", "condition_expression"}
    special = next(
        (
            s
            for s in p["special_edges"]
            if s["source_species_id"] == source_species_id
            and s["target_species_id"] == target_species_id
            and s["trigger"] == slug
        ),
        None,
    )
    if special:
        result.conditions.append(special["zh" if context.zh else "en"])
    elif slug == "level-up":
        result.conditions.append(
            context.text(
                f"等级达到 {level} 后升级进化" if level is not None else "等级提升时进化",
                f"Level up at level {level} or higher" if level is not None else "Level up",
            )
        )
    elif slug == "in-battle-level-up":
        result.conditions.append(
            context.text(
                f"等级达到 {level} 后在对战中提升等级" if level is not None else label,
                f"Level up in battle at level {level} or higher"
                if level is not None
                else context.name(trigger),
            )
        )
    elif slug == "trade":
        result.conditions.append(
            context.text(
                "交换；联系绳替代方式须依对应游戏规则核实",
                "Trade; any Linking Cord alternative depends on the game's rules",
            )
        )
        result.notes.append(
            context.text(
                "基础释义为“交换或使用联系绳”；这不表示所有游戏都支持联系绳，本途径仍以所列触发及条件为准。",
                "Linking Cord is a version-specific alternative, not a universal trade substitute.",
            )
        )
    else:
        result.conditions.append(label)
        if level is not None:
            result.conditions.append(context.text(f"等级至少 {level}", f"Level {level} or higher"))
    if (special or slug == "trade") and level is not None:
        result.conditions.append(context.text(f"等级至少 {level}", f"Level {level} or higher"))
    if slug not in p["triggers"]:
        result.unresolved.append("Unknown evolution trigger")
        result.conditions.append(context.text("触发方式待解释", "Trigger awaiting explanation"))

    resources = {
        "item": ("使用道具", "Use item"),
        "held_item": ("携带道具", "Hold item"),
        "known_move": ("学会招式", "Know move"),
        "used_move": ("使用招式", "Use move"),
        "known_move_type": ("学会此属性的招式", "Know a move of this type"),
        "party_type": ("队伍中包含此属性的宝可梦", "Have a party Pokémon of this type"),
        "party_species": ("队伍中包含", "Have in party"),
        "trade_species": ("与此宝可梦交换", "Trade for"),
        "location": ("进化地点", "Evolution location"),
        "region": ("所在地区", "Region"),
    }
    for key, (zh, en) in resources.items():
        handled.add(key)
        if method.get(key) is not None:
            result.conditions.append(f"{context.text(zh, en)}：{context.name(method[key])}")
    numbers = {
        "min_happiness": ("亲密度至少", "Minimum friendship"),
        "min_affection": ("友好度至少", "Minimum affection"),
        "min_beauty": ("美丽度至少", "Minimum beauty"),
        "min_steps": ("同行步数至少", "Minimum walking steps"),
        "min_move_count": ("指定招式使用次数至少", "Minimum uses of the specified move"),
        "min_damage_taken": ("所需承受伤害至少", "Minimum required damage taken"),
    }
    for key, (zh, en) in numbers.items():
        handled.add(key)
        if method.get(key) is not None:
            result.conditions.append(f"{context.text(zh, en)}：{method[key]}")
    booleans = {
        "turn_upside_down": ("将设备倒转", "Turn the device upside down"),
        "near_special_rock": ("靠近指定特殊岩石", "Be near the required special rock"),
        "needs_multiplayer": ("处于多人联机状态", "Be in the required multiplayer state"),
        "needs_overworld_rain": ("场景中正在下雨", "Have overworld rain"),
    }
    for key, (zh, en) in booleans.items():
        handled.add(key)
        if method.get(key) is True:
            result.conditions.append(context.text(zh, en))
    handled.update(
        {
            "gender",
            "relative_physical_stats",
            "allowed_natures",
            "time_of_day",
            "required_pokemon_form",
            "evolved_pokemon_form",
        }
    )
    if method.get("gender") is not None:
        value = method["gender"]
        result.conditions.append(
            context.text("性别：", "Gender: ")
            + (
                {1: context.text("雌性", "Female"), 2: context.text("雄性", "Male")}.get(
                    value, str(value)
                )
            )
        )
    if method.get("relative_physical_stats") is not None:
        value = method["relative_physical_stats"]
        symbol = {-1: "<", 0: "=", 1: ">"}.get(value)
        if symbol:
            result.conditions.append(
                context.text(f"攻击 {symbol} 防御", f"Attack {symbol} Defense")
            )
        else:
            result.unresolved.append("Unknown relative_physical_stats")
    if method.get("allowed_natures"):
        result.conditions.append(
            context.text("性格为以下任意一种：", "Have any one of these Natures: ")
            + "／".join(context.name(v) for v in method["allowed_natures"])
        )
    if method.get("time_of_day"):
        value = method["time_of_day"]
        result.conditions.append(
            context.text("时间：", "Time: ")
            + (
                {"day": "白天", "night": "夜晚", "dusk": "黄昏"}.get(value, value)
                if context.zh
                else value
            )
        )
    for key, label_ in (
        ("required_pokemon_form", source_label),
        ("evolved_pokemon_form", target_label),
    ):
        if method.get(key):
            result.conditions.append(
                context.text(
                    "来源形态：" if key.startswith("required") else "目标形态：",
                    "Source form: " if key.startswith("required") else "Target form: ",
                )
                + (label_ or context.name(method[key]))
            )
    if method.get("condition_expression") is not None:
        lines, notes, issues, variables = explain_expression(
            method["condition_expression"], context, method.get("evolved_pokemon_form")
        )
        result.conditions.extend(lines)
        result.notes.extend(notes)
        result.unresolved.extend(issues)
        result.variables = variables
        for variable in variables:
            result.sources.append(
                EvolutionConditionSource(
                    kind="upstream",
                    label=variable["raw_payload"]["name"],
                    url=variable["source_url"],
                    content_hash=variable["source_hash"],
                )
            )
    if method.get("version_group"):
        result.version_label = context.version_name(method["version_group"])
    for supplement in p["supplements"]:
        if (
            supplement["source_species_id"] == source_species_id
            and supplement["target_species_id"] == target_species_id
            and supplement["trigger"] == slug
        ):
            result.supplements.append(supplement)
    for key, value in method.items():
        if key not in handled and value is not None:
            result.conditions.append(
                context.text(
                    f"额外条件“{key}”待解释", f"Additional condition '{key}' awaiting explanation"
                )
            )
            result.unresolved.append(f"Unsupported field: {key}")
    if result.unresolved:
        result.status = "partial"
        result.notes.append(
            context.text(
                "部分特殊条件尚未可靠解释；原始记录已保留，请核对来源。",
                "Some conditions cannot yet be reliably explained; "
                "check the preserved source record.",
            )
        )
    return result
