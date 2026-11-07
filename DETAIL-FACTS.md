# 详情基本资料与拓展数据审查（2026-10-29）

本轮只新增详情展示与只读 API 字段。没有数据库迁移、全量同步、图片下载、容器重建或 scheduler 操作。

## 展示规则

- `baseStatTotal` 是当前 pokemon 记录 HP、攻击、防御、特攻、特防、速度六项之和，不加努力值及历史 Special。
- `eggGroups` 从当前记录所属物种的 `raw_payload.egg_groups` 读取。集中维护 15 个既有标识的中英文展示词；保留原始标识与 ID。未知标识回退易读英文，不猜测蛋组。
- `genderRate` 使用物种已有字段：0–8 为雌性占八分之几；-1 为无性别；缺失或无效显示“—”。明确标注物种比例，不把性别限定形态误作整物种比例，也不将无性别等同无法繁殖。
- `statChanges` 从当前 pokemon 的 `raw_payload.past_stats` 计算。条目的 generation 是旧数值适用的最后一代，因此改动显示从下一世代开始。稀疏历史按每项能力独立串联到后续历史值或当前值，不能直接把每条旧值都与当前值比较。
- 第一世代 `special` 在第二世代拆为特攻和特防：分别连接到当时适用的数值，并标注“特殊分拆”；即使数值相同也保留制度变动。普通相同数值不伪造改动。
- `statHistoryAvailable` 区分未收集历史字段和字段存在但无可展示改动。历史为空时不声称“从未调整”。
- 抽屉和完整详情共用组件，切换 pokemon 沿用原有状态及请求方式；细分外观共用所属 pokemon 的基础种族值和物种资料。

主要实现：`services/detail_facts.py`、`services/pokemon.py`、`schemas.py`、`PokemonDetailContent.vue`、`utils/detailFacts.ts`、前端 API 类型及双语文本。

## 本地数据覆盖

以 PostgreSQL 只读事务检查现有数据：

| 内容 | 现状 |
| --- | --- |
| 物种蛋组、雌雄比例 | 1,025 / 1,025 个物种都有资料；15 个蛋组标识均已覆盖 |
| 历史种族值字段 | 1,351 / 1,351 条 pokemon 都有字段，200 条非空 |
| 可展示历史变化 | 193 条 pokemon、379 项变化，其中 302 项为第一世代特殊拆分；其余历史条目中等值项不视为数值变化 |
| 精灵球 | 无独立资料；将来从 item 及 item-category 分类定向导入 |
| 道具 | 无 item 详情表及同步数据。452 条 pokemon 的原始 payload 有携带道具引用，进化条件另有道具引用，但不能替代道具资料 |
| 树果 | 无 berry 详情表及同步数据；将来可关联 berry.item 到 item 共享名称、效果及图片 |
| 招式 | 无 move 详情表。1,303 条 pokemon 包含招式引用，合计 833 个不同标识；原始 payload 保留学习方式、等级和版本组信息。缺名称翻译、威力、命中、PP、详细效果等独立招式资料 |
| 人物 | 无人物资料。PokéAPI v2 文档没有通用人物／训练家资源；characteristic 是宝可梦个性，不是人物。需要另行确定可维护来源 |

拓展时可分别建立 item（精灵球作为分类）、berry、move 及相应本地名称／文本和关联表，再提供列表及详情 API；人物应先确定来源。采用定向增量导入，不需要重做 pokemon 全量同步。新图片继续沿用现有 SHA-256 存储规则。本轮只完成审查，没有导入这些新资源或新增页面。

资料语义参考：[PokéAPI v2 文档](https://pokeapi.co/docs/v2#pokemon)、[Species](https://pokeapi.co/docs/v2#pokemon-species)、[Items](https://pokeapi.co/docs/v2#items)、[Berries](https://pokeapi.co/docs/v2#berries)、[Moves](https://pokeapi.co/docs/v2#moves)。

## 验证

- 后端 pytest：56 通过（含历史值逐项串联、世代边界、特殊分拆、缺数据、详情 API 字段）。Ruff 通过；mypy 29 个源文件通过。
- 前端 Vitest：13 通过；ESLint、Nuxt typecheck 通过。
- 3000 预览 Playwright：桌面与移动端各 1 项通过，覆盖皮卡丘抽屉、雌雄比例及六代防御／特防变化、磁怪完整详情、无性别、蛋组、种族值总和和移动端横向溢出检查。
- Nuxt 本机生产构建通过；因原预览正在运行，使用独立 buildDir、Nitro buildDir 及输出目录，未停用或覆盖 3000 预览。只有既有大 chunk 和依赖弃用警告。
- 全部 1,351 条原始记录的历史字段投影检查通过，没有找不到对应当前能力字段的历史项。

可复现构建：在 apps/web 激活开发环境后执行 `pnpm exec node ../../../migration-audit/build-detail-facts.mjs`。产物在 migration-audit/detail-facts-build-output，未部署到 Docker。

审查证据：项目父目录 `migration-audit/detail-facts-data-audit.json`、`detail-facts-history-verification.json`。

限制：只展示本地数据源记录的历史，不能保证涵盖所有游戏版本的差异。蛋组和雌雄比例是当前物种资料，不是逐版本繁殖规则或配对计算器。现有 Docker 8080 版本未部署本轮代码。
