# 道具与招式浏览

## 2026-10-30 连续列表与会话缓存

道具和招式列表已取消界面分页，采用首批100条＋后台分批取齐当前查询结果，按API页序逐步显示。
后端仍分页，每批100条；每种资源最多4个并发请求，离开栏目后未淘汰的查询可继续完成。
首批卡片出现后立即可操作；后续批次只在前面的页均已成功时拼接，乱序完成的批次先保留。
失败不清除成功批次，“重试剩余批次”只补缺页；数据总数发生变化或出现重复／遗漏时不宣称完整，
可使用“重新加载列表”丢弃当前查询缓存并重新获取。首次、后台加载、错误、空结果和完成分别显示。

`utils/listCache.ts` 为三个栏目的共享LRU基础；宝可梦原加载策略及缓存行为保持不变。
道具、招式共同使用 `utils/referenceListCache.ts` 和 `composables/useReferenceList.ts`，每种资源独立保存最近3组查询。
键包含资源、语言、trim且转小写的搜索词、规范化正整数筛选及有效排序；空值、默认排序、参数顺序、
旧page、详情ID、关联筛选和from等不产生新的列表缓存。滚动位置使用相同的规范化查询身份。

缓存只包含薄卡片、总数、各已成功页及完成状态，不预取完整详情或学习表，不写入localStorage。
同查询整次续传及同一页的请求分别合并；资源级请求池限制跨查询的并发。淘汰／手动失效会取消请求，
旧条目的响应不能写入替代条目，组件也只订阅当前查询。取消或失败都释放pending与loading状态。

缓存从首次创建起10分钟有效，返回／再次使用时检查；窗口重新获得焦点也检查过期并重新请求。
持续停留且不切换焦点时不会定时打断浏览，可手动重新加载。失效不会修改数据库或重新采集。
模块缓存仅由浏览器访问，SSR每个组件请求建立独立实例；整页刷新重新请求首批，再继续取齐，
仅依据URL恢复查询／详情和会话中的滚动位置，不承诺内存缓存跨刷新保存。

新查询从起点浏览；深层滚动恢复等待足够卡片渲染或结果已完整加载，再经过DOM更新与两次动画帧恢复。
如果失败时内容仍不足以恢复目标位置，会保留待恢复位置，重试补齐后再恢复。旧page参数统一删除，
不再决定数据起点；详情关联区域自己的分页保持不变。

本轮没有修改API、数据库、媒体、价格、名称、机器图片或其他待办。相关验证见
`../migration-audit/CONTINUOUS-LISTS-2026-10-30.md`。

本轮基于现有本地资料开发，不重新同步宝可梦或招式／道具数据。默认浏览不会访问 PokéAPI。
只新增道具、招式列表及详情抽屉，没有新增独立完整详情页或树果页面。

## 开发预览

- `http://127.0.0.1:3000/zh-Hans/items`
- `http://127.0.0.1:3000/zh-Hans/moves`
- 英文路径使用 `/en/items`、`/en/moves`。
- `?detail=723`、`?detail=2279` 始终以原始 ID 定位；保留两条同名记录。

在项目根目录运行 `scripts/start-web-preview.ps1` 恢复 3000。开发 API 使用现有 8001 预览服务；
媒体经 8080 代理读取现有媒体卷。Docker 前端仍等待用户明确部署命令，本轮不重建任何镜像。

## 数据与 API

`api/v1/references.py`、`services/reference_browser.py` 和 `reference_schemas.py` 提供只读查询。

| API | 用途 |
| --- | --- |
| `GET /api/v1/items` | `q`、`category`、`pocket`、`sort`、`page`、`page_size` |
| `GET /api/v1/moves` | `q`、`type`、`damage_class`、`generation`、排序及分页 |
| `GET /api/v1/items/filters`、`/moves/filters` | 上游分类、口袋、属性、伤害类别、世代及必要版本字典 |
| `GET /api/v1/items/{ID}`、`/moves/{ID}` | 单条资料、版本说明、历史、来源及关联计数 |
| `GET /api/v1/items/{ID}/holders` | 独立 pokemon ID、游戏版本、原始 rarity |
| `GET /api/v1/items/{ID}/machines`、`/moves/{ID}/machines` | 原 machine ID、item ID、move ID、版本组 |
| `GET /api/v1/items/{ID}/evolutions` | 道具引用角色、链及原路径；结构化定位实际形态，保留 form 查询参数 |
| `GET /api/v1/moves/{ID}/learners` | 独立 pokemon ID、形态名、版本组、学习方式、等级和顺序 |

分页上限 100；列表首批及后续每批100条、连续浏览；详情关联每页24条。关联支持版本组、学习方式或游戏版本筛选。
排序为 `id`、`id_desc`、`name`；招式另有 `power_desc`、`priority_desc`，空值最后，ID 稳定打破同值。
所有接口支持 `locale=zh-Hans|en`。数字搜索精确匹配 ID；其他文字按标识和已存名称作字面子串搜索。
详情接受唯一 slug；一个 slug 对应多个 ID 时返回 409 和候选 ID，页面关联始终使用数字 ID。

常用资料直接使用已有结构化字段及关联，字典向 API 返回原始 `resource_id`，不把本地字典主键当原始 ID。
名称采用请求语言 → 英文 → 原标识；说明按每个“文本种类＋版本上下文”回退，保留上游语言标记。
原始 JSON、来源 URL、采集时间、哈希、同步记录保持原样；列表不载入原始 JSON，详情不返回整份来源 JSON。
复杂华丽大赛组合等仍可从来源 JSON 核验，本轮没有为这些字段单独增加页面或额外采集。

## 图片归属与最小迁移

原 `media_asset` 仅支持 pokemon／pokemon-form 归属；不能把 item #25 当成 pokemon #25。
因此迁移 `0006_item_media` 仅新增 `item_media`，不修改原表列或旧媒体关联。

`item_id` 是主键及外键，另存默认图片来源、状态、SHA-256、共享相对地址、实际格式、大小、尺寸、帧数、
尝试次数、错误及更新时间；来源 URL、状态和哈希有索引。图片归属由表和外键决定，不由文件目录或数值相等推断。

只读取 `item.sprites.default`。每个来源地址只请求一次；按实际图片格式验证，通过 SHA-256 复用已登记文件，
新内容保存为 `version-sprites/{hash前两位}/{hash}.{实际格式}`。不同 ID 可共用地址，记录保持独立。
没有新增历代道具图片分类，没有转换图片格式或动画。

定向命令（在已配置正确 DATABASE_URL、MEDIA_ROOT、共享卷写权限的 Python 环境内）：

```powershell
python -m pokedex_api.sync.item_media --limit 20 --concurrency 6 --report item-media-pilot.json
python -m pokedex_api.sync.item_media --concurrency 6 --report item-media-full.json
python -m pokedex_api.sync.item_media --retry-failed --report item-media-retry.json
```

该命令只登记／处理道具默认图，不启动 scheduler，不调用宝可梦同步。默认续跑 pending／失败／损坏项；
已完成项不重复下载，404 项只有显式 `--retry-failed` 才再次尝试。每批有进度日志，每个 URL 独立提交状态，
单条失败及来源保存在数据库和报告中。使用与现有媒体任务相同的 PostgreSQL advisory lock，避免同时写入。
如果上游默认来源经其他已授权任务发生变化，下一次定向执行只重置该道具的新媒体状态，不删除旧文件。

本机媒体在 Docker 卷内，不能把命令误指向宿主机空的 `data/media`。本次执行通过原 API 容器的临时
`PYTHONPATH=/tmp/pokedex-item-media` 加载新程序；未替换运行服务源码、容器或镜像。报告在
`../migration-audit/item-media-full.json` 和 `item-media-repeat-final.json`。

图片懒加载，失败／无图时显示名称和占位文字；处理了 SSR 图片早于水合失败的情况，快速切换后不沿用上一张失败状态。

## 价格和空值规则

价格按“道具＋版本组＋货币”展示，买价与卖价分别处理。版本组选项不合并同一世代的不同游戏。

- 无整条价格记录：显示“暂无价格资料”，不据此判断所有游戏都不可买卖。
- 已有记录中的显式 null：只在该版本组／货币下显示不可购买或不可出售。
- 上游省略字段：显示未提供；明确的 0 保持 0。
- 旧 `cost` 缺少版本／货币上下文，只在来源折叠栏保留，绝不补作购买价。
- 价格不全是允许的数据状态，不触发额外采集或人工补录。

null 语义依据 [PokéAPI ItemPrice 文档](https://pokeapi.co/docs/v2/#item-prices)。
招式威力、命中、PP 等空值保持空值，不转换成 0 或“必中”。历史数值独立列出上游版本组，
不填补未记录项，不把引入世代解释为唯一适用世代。树果生长时间为每阶段小时数，收获量注明第四世代，
依据 [PokéAPI Berry 文档](https://pokeapi.co/docs/v2/#berries)。

## 导航和状态

`q`、筛选、`sort`、`detail` 存在 URL，旧列表 `page` 参数自动移除；关联的 `rel`、`rel_page`、`rel_vg`、`rel_method`、
`rel_version` 同样保存在 URL。列表滚动位置按“列表路径＋真实列表查询”存入会话，不因详情或关联分页而变化。
详情打开／关闭不重新请求整份列表；刷新、前进后退恢复对应记录和查询。列表经API分页连续取齐薄卡片，不加载全库详情。

关联另一种资料时带安全的站内 `from`，提供“返回来源”；关联宝可梦使用原数字 ID／必要 form 查询，
进入现有宝可梦详情并显示“返回道具列表”或“返回招式列表”，返回后恢复原资料抽屉及上下文。
原宝可梦抽屉内部关联方式保持不变。

详情请求使用 AbortController 和递增请求号，销毁／切换时取消旧请求；旧响应不能覆盖新记录。
移动端模态、Escape、焦点恢复、Tab 循环及长名称换行已覆盖。

## 备份、回滚和核验

迁移前记录 `../migration-audit/items-moves-before.json` 全表摘要，并用 `pg_dump -Fc` 保留一致性备份：
`../migration-audit/pokedex-before-items-moves-ui.dump`。
SHA-256：`DB14C1F5D7F6573074C2359B1228FFCCDBCBF8C6C663D80493B064AB19FE2AB3`。
迁移使用 5 秒锁等待、60 秒语句超时；无业务表重写。

只在另行决定回滚时先停用新功能代码，审查 `scripts/items_moves_rollback.sql`；它检查迁移版本后仅删除新增表，
恢复迁移标记，不删除媒体文件或旧表。本次没有执行回滚。完整数据库备份供异常恢复备用，不自动覆盖运行库。

只读验证：

```powershell
apps/api/.venv/Scripts/python.exe scripts/verify_reference_pages.py --output ../migration-audit/items-moves-integrity.json
```

它逐页对照数据库完整 ID 集合、核对关联及价格行，实际读取本地媒体检查哈希，不请求上游。
保护验证：`items-moves-before.json` 与 `items-moves-after.json` 除迁移标记及新表外一致。
Navicat 示例见 `scripts/reference_page_examples.sql`。完整交付结果见
`../migration-audit/ITEMS-MOVES-RESULT-2026-10-29.md`。
