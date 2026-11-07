# 招式、道具和树果数据层

本轮为现有 PostgreSQL 增加数据层，不增加前端页面。使用 PokéAPI 完整分页列表发现
`move`、`item`、`berry`；保留原有 Pokémon、形态、图鉴编号、链接及所有图片关联。
本机连接继续为 `127.0.0.1:15432`，密码读取根目录 `.env`，不写入报告或命令行。

## 表结构与来源

迁移 `0003_reference_data`、`0004_item_prices`、`0005_reference_identifiers`
共新增以下 18 张表，不修改原有宝可梦／媒体表列或重写旧记录：

| 表 | 主要字段与用途 |
| --- | --- |
| `move` | 原始 ID、英文标识、来源记录；威力、命中、PP、优先度、效果概率；属性、伤害类别、目标、世代、状态、招式类别及华丽大赛字典 FK；完整 meta |
| `move_stat_change` | 招式、原始顺序、能力字典及变化值 |
| `move_past_value` | 招式、原始顺序、版本组、旧属性／威力／命中／PP／效果概率和完整历史 JSON |
| `item` | 原始 ID、英文标识、来源记录；官方分类、旧格式 cost（有才存）、投掷威力／效果、图片来源元数据 |
| `item_price` | 道具、原始顺序、版本组、货币、购买价、出售价格和完整原始价格 JSON；区分 null 与 0 |
| `item_attribute_link` | 道具与官方道具属性的关联 |
| `item_game_index` | 道具、世代和该世代游戏索引 |
| `catalog_machine` | 原始 machine ID、道具、招式、版本组及来源记录 |
| `berry` | 原始 ID、英文标识、来源记录、唯一 item_id；硬度、自然之恩属性／威力、生长时间、收获数、尺寸、光滑度、土壤干燥速度 |
| `berry_flavor_link` | 树果、风味字典和原始 potency |
| `catalog_dictionary` | 字典类型、PokéAPI resource_id、英文标识、来源记录及顺序 |
| `catalog_dictionary_link` | 字典之间的真实 JSON 路径与关联，例如道具分类→口袋、版本→版本组→世代 |
| `pokemon_move` | 独立 pokemon_id、move_id、版本组、学习方式、等级、学习顺序、完整 detail JSON；原始数组位置构成主键 |
| `pokemon_held_item` | 独立 pokemon_id、item_id、版本、原始 rarity 和 detail JSON；原始数组位置构成主键 |
| `evolution_item_reference` | 进化链、完整 JSON 路径、引用角色、item_id 和原始引用；不改动进化条件 |
| `catalog_sync_entry` | 每条资源／本地关联的状态、尝试次数、错误、采集时间、已整理哈希、run_id |
| `catalog_discovery_page` | 每轮完整分页响应、URL、哈希和采集时间，便于检查 count、分页及重复记录 |
| `catalog_reference_issue` | 按来源、位置、目标和原因生成唯一指纹；保留历史问题及 resolved 状态 |

实体的 ID 均为 PokéAPI 原始 ID。字典也保留合法的负数 ID，例如 move-ailment/-1。
英文标识不强制唯一：上游存在不同 ID 同名的记录，保持独立，不合并／改名。
字典的 `id` 是本地关联键，`resource_id` 才是原始 ID，
查询时同时保留 `resource_type`。实体、字典和 machine 通过 `source_record_id` 复用现有
`source_record` 的来源 URL、完整 JSON、SHA-256 内容哈希和 fetched_at。
常用筛选和关联字段均有索引；FK 保证关联目标存在。复杂字段以来源 JSON 为准，不丢弃。

精灵球、树果对应道具都保留在 item 中，通过官方 item-category→item-pocket 关联分类，
不用道具名称猜测。berry 不另建多语言名称／效果副本，查询函数通过 item_id 读取 item。

复用 `localized_name`、`localized_text` 保存上游提供的简中、繁中和英文。说明保留
`version:`、`version_group:` 或 `generation:` 上下文；效果变更标记为 past_effect 等，
招式 past_values 也单独保存。其他语言和所有原始排版仍完整保留在 source_record。
`services/reference_catalog.py` 提供名称的请求语言→英文→源标识回退；说明按每个
text_kind／版本上下文分别回退英文，不用一个最新说明覆盖历史，也不自动翻译。

## 采集边界与运行命令

在仓库根目录运行，使用既有 Python 3.13 虚拟环境。下面的本机包装器从 `.env` 读取
连接信息，只把 Compose 的 db 主机替换为当前本机映射，不显示密码：

```powershell
# 只在新环境尚未迁移时执行；已迁移环境会保持当前版本。
.\apps\api\.venv\Scripts\python.exe scripts/reference_data_db.py upgrade

# 完整定向同步；默认复用已缓存且成功的资源，仍重新检查三类完整分页列表。
.\apps\api\.venv\Scripts\python.exe scripts/reference_data_db.py sync --report ..\migration-audit\reference-data-latest.json

# 重取一个资源，或只重试失败／缺失条目。
.\apps\api\.venv\Scripts\python.exe scripts/reference_data_db.py sync --only move:33 --refresh
.\apps\api\.venv\Scripts\python.exe scripts/reference_data_db.py sync --retry-failed

# 恢复指定的 reference-data run。替换实际 run_id。
.\apps\api\.venv\Scripts\python.exe scripts/reference_data_db.py sync --resume-run 10

# 只读完整性检查。
.\apps\api\.venv\Scripts\python.exe scripts/verify_reference_data.py --output ..\migration-audit\reference-data-integrity.json
```

其他环境已正确设置 DATABASE_URL 时，直接运行
`python -m pokedex_api.sync.reference_cli`，参数相同；不要运行旧的全量同步入口替代此命令。
`--refresh` 重取本次范围缓存，`--only RESOURCE:ID` 可定点处理；`--limit N --skip-links`
仅用于小样本，样本之外的依赖会如实报告，不保证小样本全部关联已完整。
`--stop-after-fetch N` 在已提交的检查点退出，供中断续跑验证；不代表采集完成。

关联字典只允许：type、generation、stat、version、version-group、move-damage-class、
move-target、move-category、move-ailment、move-learn-method、item-category、item-pocket、
item-attribute、item-fling-effect、berry-firmness、berry-flavor、contest-type、contest-effect、
super-contest-effect、currency。只取实际引用的 machine。有限集合内补齐依赖，不追踪人物、地点、
宝可梦、形态、特性、遭遇等其他资源；字典原始 JSON 中的无关反向引用只保留，不采集。
已有 type、generation、stat 的来源和多语言记录直接复用，不改写现有站点数据。

默认并发 4（允许 1～8），HTTP 超时 30 秒，指数抖动重试最多 5 次，分页大小 100。
内容落入 source_record 后才整理，每条事务提交；本地 Pokémon 关联每个记录独立事务，
按主键分批读取。PostgreSQL advisory lock 防止两个定向同步同时写入。
逻辑尝试次数是每次资源采集次数，不等于底层最多五次 HTTP 请求数。

退出码 0 表示所有已登记范围和引用成功；2 表示 partial／interrupted，应查看报告和状态表；
未捕获错误退出时保留已提交进度。硬中断可能让 sync_run 停在 running，连接关闭会释放锁，
可按原 run_id 续跑。单条远端失败不删除旧来源或实体，404 标为 missing。
本地存在而新列表不再列出的资源同样保留并报告。无自动删除、清库或全量重导入。

## 备份、迁移和回滚

迁移前基线：`../migration-audit/reference-data-before.json`。
一致性备份：`../migration-audit/pokedex-before-reference-data-20261029.dump`，
37,612,128 字节；SHA-256：
`6FC1954D09C8693559A8711EFB235CA8DD3CC4C0D79758BF4F9B1496797A6234`。
已用 pg_restore --list 校验目录可读。备份保留现有全部数据库内容，媒体卷无需更改。

迁移事务设置 lock_timeout=5s、statement_timeout=60s，只新建表和索引，以及放宽新增表的
英文标识唯一约束；不进行原有大表
重写。恢复网站无需重建 API／前端容器。进化、图片及列表查询继续使用现有数据结构。

回滚方式（已准备，本轮不执行）：先停止此定向采集并导出新增数据；审查后执行
`scripts/reference_data_rollback.sql`，仅撤销这 18 张新增表并恢复原迁移版本。
脚本带当前版本检查及事务，不会自动删除共享
source_record／localized_name／localized_text 中新增的资源来源；如需完全清理，按本轮
资源类型和运行记录定向清理，保留旧 type／generation／stat 等来源。
0005 单步降级恢复唯一约束时，如存在合法同名记录会原子拒绝，不会合并、删改记录；
因此整体撤销使用明确列出表名的上述脚本，而非逐步恢复旧约束。完整数据库恢复应
先用 pg_restore 导入独立数据库并验证，再安排切换，不能向运行中的现有库直接 --clean。

## 检查与结果

本轮最终数量、语言覆盖、完整性、重复运行和中断／重试证据详见
`../migration-audit/REFERENCE-DATA-RESULT-2026-10-29.md`。
Navicat 示例查询：[scripts/reference_data_examples.sql](scripts/reference_data_examples.sql)。
同步进度和失败可通过示例 SQL 第 9 组查询，不依赖前端页面。

本轮不增加页面或数据 API，不启动 scheduler，不执行宝可梦全量同步，不下载图片；图片
来源元数据保留，未来仍应交给现有 SHA-256 媒体机制。远端缺失中文、效果或历史字段
时保持缺失并回退已有英文，不补造内容。已有 Pokémon 原始资料的历史范围不因本次
采集而刷新；远端新出现的 Pokémon 不会自动入库。
