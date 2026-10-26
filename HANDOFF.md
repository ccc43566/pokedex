# Pokédex 项目交接

> 状态快照：2026-10-25（亚洲／上海），基于本地 `main` 的 `98650e7` 及当天只读检查。此文件描述交接时的状态；以后以实际代码、数据库和容器检查结果为准。

## 目标与已经确认的要求

- 构建中文优先、支持英文的宝可梦图鉴；正常浏览从本地数据库和媒体卷读取，不在每次页面访问时查询 PokéAPI。
- 宽屏图鉴每行 8 张紧凑卡片；当前列表不翻页，后台按 API 单次最多 100 条分批取回所有筛选结果。首页展示 8 张卡片。
- 筛选控件先编辑草稿，点击“筛选”才应用。长列表滚动时，筛选栏停在主菜单下。选中卡片有明确标记；点击卡片打开右侧详情抽屉，并保持列表上下文。
- 详情页/抽屉可按宝可梦或形态、世代、游戏和图片类型查看 PokéAPI `sprites.versions` 的原始 PNG、GIF、WebP。源字段为 `null` 属于上游没有独立图片；雌性图缺失时只允许同一游戏的默认图作为带说明的界面回退。
- 保留现有四类预览图和媒体卷；不同世代／游戏的关联及原 URL 保留在数据库中，下载文件可按 URL 和 SHA-256 去重。
- **目前暂停补齐图片。** 不运行 `--versions-only`、`--media-only` 或其他会触发媒体下载的同步命令；定时同步器也应保持停止。用户尚未决定何时恢复。
- 开发流程：8080 端口运行 Docker 后端和现有站点，Nuxt 在本机 3000 端口热更新，`/api/v1` 和 `/media` 经开发代理转到 8080；一轮修改后再做类型检查、构建和截图，验收后才重建 Docker 服务。

## 架构和重要文件

| 路径 | 用途 |
| --- | --- |
| `README.md` | 项目总览和原有启动说明；其同步步骤会下载数据，当前暂停期不要执行。 |
| `docker-compose.yml`、`Caddyfile` | PostgreSQL、API、定时器、一次性媒体同步、Nuxt、Caddy 的服务定义及 8080 路由。 |
| `.env.example` | 环境变量模板；真实 `.env` 被 Git 忽略。 |
| `apps/api/pyproject.toml`、`apps/api/uv.lock`、`apps/api/Dockerfile` | Python 依赖、锁文件和 API 镜像。 |
| `apps/api/src/pokedex_api/sync/cli.py`、`sync/version_sprites.py` | PokéAPI 同步入口和历代图片采集逻辑。 |
| `apps/api/src/pokedex_api/models.py`、`apps/api/alembic/versions/0002_version_sprites.py` | `version_sprite` 数据模型和迁移。 |
| `apps/api/src/pokedex_api/api/v1/pokemon.py`、`services/version_sprites.py` | 图鉴及历代图片 API。 |
| `apps/web/package.json`、`pnpm-lock.yaml`、`nuxt.config.ts` | 前端脚本、锁文件、开发代理和运行时配置。 |
| `apps/web/pages/pokemon/index.vue`、`components/PokemonCard.vue`、`components/PokemonDetailDrawer.vue` | 全量列表、选中态及详情抽屉。 |
| `apps/web/components/PokemonVersionGallery.vue`、`server/api/version-media/[id].get.ts` | 历代图片浏览与旧 API 镜像期间的开发预览快照回退。 |
| `scripts/report_version_sprites.py`、`scripts/export_version_media.py` | 图片采集统计、开发预览 JSON 快照导出。 |
| `ENVIRONMENT.md` | 软件、命令、环境变量及 Windows 迁移步骤。 |

## 当前完成情况

- 前后端、基础图鉴、筛选、抽屉、粘性搜索栏和历代图片画廊代码已在仓库中。Git 远端为公开仓库 `https://github.com/ccc43566/pokedex`，本地基线提交为 `98650e7`。
- 本机数据库有 1,351 条 `pokemon`、1,579 条 `pokemon_form`。`version_sprite` 有 66,112 条 `downloaded`、489,918 条正常 `null`、88,570 条 `pending`；未见 `download_failed` 或 `corrupt` 状态。非空 URL 去重后为 80,598 个，已下载记录的内容哈希去重后为 27,323 个。这些数字是关联／URL／哈希的不同口径，不能都当成文件数。
- 本机 Docker 卷 `pokedex_pokedex_media` 挂载到 `/app/media`，当前约 7.9 GB；`pokedex_pokedex_postgres` 的数据库目录约 765 MB。两卷均不在 Git 中，大小只是交接日的粗略占用。
- 本机 `data/version-media/` 有 1,351 个被 Git 忽略的 JSON 快照，约 181.3 MiB；它们是开发预览回退数据，不是图片原文件。宿主机 `data/media/` 只有跟踪的 `.gitkeep`；实际图片在 Docker 卷中。
- 本机 Docker 的 `db`、`api`、`web`、`caddy` 在检查时运行。`scheduler` 原本运行；检查日志显示最近两次因上游版本未变而没有导入，本次已按“暂停补图”要求停止。当前容器镜像可能旧于仓库源码：数据库存在 `version_sprite` 表，但 `alembic_version` 仍是 `0001_initial_schema`；新版迁移 `0002_version_sprites` 设计为识别已存在的表。
- 先前已针对历代图片做后端单元测试、前端类型检查和开发预览浏览器检查。它们不等同于当前仓库在新电脑上的完整验证；迁移后需要重跑。当前 Docker 服务尚未统一重建为最新源码。

## 关键决定及原因

1. **先保留当前不完整图片库。** `null` 是 PokéAPI 的正常缺图；`pending` 是尚未下载。用户要求先迁机、暂不补图，因此迁机不应顺带执行同步。
2. **数据库和媒体卷一起迁移。** 数据库保留源 URL、世代／游戏／形态关联及文件路径；只有媒体卷则无法恢复关联，只有数据库则图片路径会失效。
3. **开发预览继续用 3000，Docker 站点用 8080。** Nuxt 配置已有代理，可直接热更新 Vue/CSS。现有开发预览可用 JSON 快照读取历代图片；重建新版 API 后应由真实 `/api/v1/pokemon/{id}/version-sprites` 提供。
4. **采用锁文件复现依赖。** Python 使用 `uv.lock`，前端使用 `pnpm-lock.yaml`；迁移时不要从本机复制虚拟环境或 `node_modules`。

## 未提交／未跟踪但运行相关的内容

交接前 `git status` 未显示已修改的跟踪文件，`git ls-files --others --exclude-standard` 未显示普通未跟踪文件；本次新建的两份文档应提交后再迁机。下列内容被 `.gitignore` 排除，GitHub 克隆**不会**包含：

| 内容 | 是否需要单独备份 | 说明 |
| --- | --- | --- |
| 根目录 `.env` | 需要安全迁移或在新电脑重新填写 | 有数据库口令等敏感配置；不要提交到公开仓库或写进文档。 |
| Docker 卷 `pokedex_pokedex_postgres` | 若要保留当前数据，必须备份 | 建议用 `pg_dump` 生成逻辑备份，勿在数据库运行时直接复制卷目录。 |
| Docker 卷 `pokedex_pokedex_media` | 若要保留当前图片，必须备份 | 包含四类预览图和已下载的历代图片；约 7.9 GB。 |
| `data/version-media/*.json` | 可选 | 1,351 个快照；仅用于当前旧 API 镜像下的本地开发画廊，未来可从数据库重导。若在重建 API 前就要完整复现开发预览，另行备份。 |
| `apps/api/.venv/`、`apps/web/node_modules/`、`.nuxt/`、`.output/` | 不需要 | 由依赖安装／构建命令重建，复制 Windows 路径下的这些目录反而容易出错。 |
| `data/*.log` 等日志 | 通常不需要 | 诊断记录，不是运行数据；如需追查之前的采集过程可另存。 |

## 已知问题与未完成事项

- 历代图片采集尚未完成：88,570 条关联为 `pending`。现在不应把“未提供”与“未下载”混淆，也不应承诺各世代已全部覆盖。
- 当前数据库表和 Alembic 标记暂不同步（表已存在，版本号为 `0001_initial_schema`）。新 API 镜像启动时会运行 `alembic upgrade head`；迁移脚本有现存表判断，但仍应在数据库备份后验证标记升至 `0002_version_sprites`。
- 8080 所用 API／Web 镜像未与最新源码统一重建；在新电脑备份恢复完成后重建 `api web caddy`，检查画廊从真实 API 加载。若只克隆代码、不恢复数据库与媒体卷，图鉴会没有现有数据与图片。
- 当前前端“显示全部”会向最多 100 条的 API 发多个请求；迁移后的性能和浏览器占用应在目标电脑实测。
- 公开仓库仅承载代码和文档。图片版权、PokéAPI 可用性及未来公网部署方式尚未确认；当前记录的是本机 Docker／开发预览，不等于已完成公网部署。

## 下一步具体操作

1. 在原电脑确认 `git status` 仅有预期文档变更；将两份文档提交并推送。把数据库逻辑备份和媒体卷备份存到 **GitHub 之外** 的安全位置；`.env` 可在新电脑从 `.env.example` 重新生成，不必搬运旧文件。若需要保留旧 API 开发预览，再带上 `data/version-media/`。
2. 在新电脑按 `ENVIRONMENT.md` 安装 Git 与 Docker Desktop，克隆仓库；若要原样开发前端，再配置 Node 24、pnpm 11.19.0；本地开发 API 才需 Python 3.13 和 uv。
3. 准备新电脑 `.env`。恢复数据库与媒体卷后，只启动 `db api web caddy`；不要启动 `scheduler` 或 `media-sync`。备份／恢复示例和校验命令见 `ENVIRONMENT.md`。
4. 检查 `http://localhost:8080/api/v1/health`、中文图鉴、图片和妙蛙种子的历代画廊，再打开 3000 开发预览。运行类型检查、构建、后端测试和必要的浏览器检查。
5. 等用户明确决定恢复补图时，先检查目标盘空间与当前状态，再决定是否运行 `--versions-only`；恢复定时器也应单独决定。
