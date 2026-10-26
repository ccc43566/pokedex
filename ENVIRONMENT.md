# Pokédex Windows 环境与迁移

> 核对日期：2026-10-25。以下“版本”区分源码要求和原电脑实测；未规定最低 Docker／Git 版本。命令以 PowerShell、仓库根目录为起点。本文不包含真实口令、令牌或 `.env` 的值。

## 软件和依赖来源

| 软件 | 项目要求／用途 | 原电脑实测 |
| --- | --- | --- |
| Windows 上的 Git | 克隆公开仓库；项目未限定版本 | Git 2.55.0.windows.3 |
| Docker Desktop（Linux 容器）及 Compose | 推荐运行整套服务；Compose 文件定义数据库、API、Web、Caddy | Docker Engine/Client 29.8.2；Compose 5.5.1 |
| Node.js | 本机 Nuxt 开发建议 24；Web Dockerfile 使用 `node:24-alpine` | PATH 中 `node` 为 20.20.2，**不符合开发建议**；另有可用 Node 24.22.1 安装包 |
| pnpm | `apps/web/package.json` 固定包管理器为 `pnpm@11.19.0`，由 Corepack 管理 | 原电脑 PATH 中 `pnpm` 报“未配置活动 Node 版本”；已另备 pnpm 11.19.0 文件，但迁机时应重新配置 |
| Python | 只有在 Windows 上直接开发 API 时需要；`apps/api/pyproject.toml` 要求 `>=3.13`，代码／Docker 使用 3.13 | API 虚拟环境 3.13.14；PATH 中 Python 为 3.14.6，不能据此认定已用项目目标版本 |
| uv | Python 依赖安装器，使用 `apps/api/uv.lock`；API Dockerfile 自带 uv | uv 0.11.32；项目没有锁定 uv 工具自身版本 |
| Microsoft Edge 或 Playwright Chromium | 只供浏览器端到端测试和截图 | Edge 的具体版本未核对 |

仅使用 Docker 跑站点时，新电脑不需要在 Windows 宿主机另装 Python、Node 或 pnpm；Docker 构建会在镜像内安装锁定依赖。依赖安装／镜像拉取都需要网络。数据库镜像为 `pgvector/pgvector:pg17`；API 基础镜像为 `ghcr.io/astral-sh/uv:python3.13-bookworm-slim`；Web 基础镜像为 `public.ecr.aws/docker/library/node:24-alpine`；反向代理为 `public.ecr.aws/docker/library/caddy:2-alpine`。这些浮动标签的确切镜像摘要没有锁定，目标电脑构建结果可能随仓库更新而变化。

## 项目目录与环境变量

`pyproject.toml` 和 `uv.lock` 负责 Python 依赖，`apps/web/package.json` 和 `pnpm-lock.yaml` 负责前端依赖；它们不保存数据库口令或运行地址。**不必从原电脑搬运 `.env`**：在新电脑从 `.env.example` 生成根目录 `.env`，自行设置新密码，并让 `DATABASE_URL` 中的用户名、密码、数据库名与 `POSTGRES_USER`、`POSTGRES_PASSWORD`、`POSTGRES_DB` 一致。若密码有 URL 特殊字符，`DATABASE_URL` 中须正确编码。真实 `.env` 不在 Git 中，也不要提交到公开仓库。

```powershell
Copy-Item .env.example .env
```

| 名称 | 来源／用途 |
| --- | --- |
| `POSTGRES_DB`、`POSTGRES_USER`、`POSTGRES_PASSWORD` | Compose 初始化 PostgreSQL。按下文的 `pg_dump`／`pg_restore --no-owner --no-acl` 逻辑备份恢复到**新建空库**时，可以在新电脑使用新的用户、密码和数据库名；`DATABASE_URL` 必须与之匹配。若改用 Docker Hub 直接搬运原始数据库卷，则数据库已初始化，不能靠修改 `.env` 重设旧用户的密码。 |
| `DATABASE_URL` | API／scheduler／media-sync 的 SQLAlchemy/asyncpg 连接串；Compose 网络中数据库主机为 `db`。本机直接跑 API 时需改为本机可访问的数据库地址。 |
| `POKEAPI_BASE_URL`、`POKEAPI_USER_AGENT` | 后台同步访问 PokéAPI；浏览现有本地数据不需要在页面请求时访问上游。 |
| `SYNC_CONCURRENCY` | 同步并发数。`SYNC_PAGE_SIZE` 也在 API 设置中，未出现在示例文件。 |
| `MEDIA_ROOT`、`MEDIA_PUBLIC_PATH` | API 的媒体文件根目录和公开路径；Compose 中实际固定挂载 `/app/media`，公开路由 `/media`。 |
| `APP_PORT` | Caddy 对宿主机开放的端口，默认 8080。 |
| `NUXT_API_BASE` | Nuxt 服务端访问 API 的基址；Compose 覆盖为 `http://api:8000`。本机 `pnpm dev` 默认转到 `http://localhost:8080`。 |
| `NUXT_PUBLIC_API_BASE` | 浏览器 API 路径前缀，默认 `/api`。 |
| `NUXT_PUBLIC_SITE_URL` | 网站地址；Compose 默认为 `http://localhost:8080`，本机开发默认为 `http://localhost:3000`；未列在 `.env.example`。 |
| `POKEDEX_DEV_BACKEND` | 可选：把 Nuxt 开发代理 `/api/v1`、`/media` 改指向另一后端，默认 `http://localhost:8080`。 |
| `APP_NAME`、`APP_VERSION`、`ENVIRONMENT`、`CORS_ORIGINS` | API 设置中的可选值；见 `apps/api/src/pokedex_api/config.py`。 |
| `VERSION_SPRITE_LIMIT`、`VERSION_SPRITE_OWNER_ID`、`VERSION_SPRITE_CONCURRENCY`、`VERSION_SPRITE_SKIP_MATERIALIZE` | 历代图片采集器的可选控制项；**当前暂停采集，不需设置或运行**。 |
| `VERSION_EXPORT_ROOT`、`VERSION_EXPORT_ID` | 开发预览 JSON 快照导出脚本的可选值。 |
| `PLAYWRIGHT_USE_EDGE`、`CI` | E2E 测试选用系统 Edge、CI 重试设置。 |

`NODE_ENV` 和 `npm_lifecycle_event` 由 Nuxt/包管理器设置，用于判断开发模式；通常不手填。当前真实 `.env` 只核对了**变量名称**，没有读取或记录其值。

## 服务、端口与当前暂停状态

`docker-compose.yml` 定义：`db`（PostgreSQL 17 + pgvector）、`api`（FastAPI，容器内 8000）、`web`（Nuxt，容器内 3000）、`caddy`（宿主机 8080）、`scheduler`（每周同步，启动后立即先执行一次）、`media-sync`（一次性媒体同步）。Caddy 把 `/api/*`、`/media/*`、`/docs*`、`/openapi.json` 转给 API，其余转给 Web。数据库和 API 端口没有直接暴露给宿主机。

**暂停补图期间只启动下列服务，不使用无服务名的 `docker compose up -d`：**

```powershell
docker compose -p pokedex up -d --build db api web caddy
docker compose -p pokedex ps
```

站点：`http://localhost:8080/zh-Hans/pokemon`；健康检查：`http://localhost:8080/api/v1/health`。`api` 镜像入口会自动执行 `alembic upgrade head`。当前原电脑的定时器已停止；新电脑也应维持停止。`docker compose down` 不带 `-v` 会保留卷；**不要在要保留数据时使用 `down -v`**。

## 本机开发和依赖安装命令（在新电脑执行）

前端在 `apps/web` 下安装锁定依赖并运行；先保证 PATH 中的 Node 为 24.x，Corepack 能提供 pnpm 11.19.0。原电脑当前 PATH 的 Node 20／pnpm 异常，不能直接照搬配置。

```powershell
cd apps/web
corepack pnpm install --frozen-lockfile
corepack pnpm dev
```

浏览器打开 `http://127.0.0.1:3000/zh-Hans/pokemon`。开发代理把 `/api/v1` 和 `/media` 转到 8080，Vue/CSS 保存后自动热更新。若用 `pnpm` 命令，先确认 `pnpm --version` 为 `11.19.0`。离开 `apps/web` 后回仓库根目录可运行 `cd ../..`。

若确需在 Windows 宿主机直接运行 API，先准备 Python 3.13 和可访问的 PostgreSQL 17/pgvector，调整本机用 `DATABASE_URL` 与 `MEDIA_ROOT`；**当前 Compose 没有把 PostgreSQL 5432 暴露到宿主机**，需自行增加安全的本机连接方式。随后在 `apps/api` 运行：

```powershell
uv sync --frozen --python 3.13
uv run alembic upgrade head
uv run uvicorn pokedex_api.main:app --reload
```

宿主机直跑 API 的数据库网络、媒体目录和环境变量值在迁机前未验证，因此推荐先使用 Docker API + 3000 Nuxt 的既有开发流程。不要把原电脑 `.venv`、`node_modules` 或构建目录复制过去。

## 检查和测试命令

```powershell
cd apps/web
corepack pnpm typecheck
corepack pnpm build
corepack pnpm test
corepack pnpm lint
$env:PLAYWRIGHT_USE_EDGE = '1'  # 已安装 Edge 时使用；另可安装 Playwright Chromium
corepack pnpm e2e
```

E2E 配置会启动或复用 3000 开发服务；需先有 8080 后端和数据库。API 测试：

```powershell
cd apps/api
uv run pytest
uv run ruff check .
uv run mypy src
```

这些是项目提供的命令，并非声称交接日已全部通过。跨电脑恢复后应实际运行。`apps/web/scripts/capture-version-gallery.mjs` 是另一个开发预览截图检查脚本，使用系统 Edge，执行前需先启动 3000 服务。

## Git 不带走的数据及备份／恢复示例

原电脑的普通未跟踪文件检查结果为空；两份新文档提交后应再次检查。以下被忽略或在 Docker 卷中，必须按需求独立处理：根目录 `.env` 可在新电脑从 `.env.example` 重建，不必复制；`pokedex_pokedex_postgres` 的数据库和 `pokedex_pokedex_media` 的原始图片若要保留现状则必须备份；可选的 `data/version-media/` 预览快照（1,351 个、约 181.3 MiB）可另存。`data/media/` 在宿主机只有 `.gitkeep`，**不是**图片备份。`.venv`、`node_modules`、`.nuxt`、`.output` 和日志可重建或不影响运行。

两份文档推送后，新电脑可在 PowerShell 中克隆公开源码；数据库和图片备份需另行安全传输，不能仅靠这条命令：

```powershell
git clone https://github.com/ccc43566/pokedex.git
cd pokedex
```

以下示例在原电脑的仓库根目录执行，备份目录请放在 Git 仓库之外，且有足够空间。示例假设 Compose 项目名为 `pokedex`，与当前卷名一致；其他项目名要先用 `docker volume ls` 核对。数据库采用逻辑备份，媒体卷在采集暂停后归档；备份文件可能含敏感数据，不要上传到公开 GitHub。

```powershell
$backupDir = 'D:\pokedex-transfer'
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
docker compose -p pokedex exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/pokedex.dump'
docker cp pokedex-db-1:/tmp/pokedex.dump "$backupDir\pokedex.dump"
docker run --rm -v pokedex_pokedex_media:/source:ro -v "${backupDir}:/backup" alpine:3.20 tar -C /source -cf /backup/media.tar .
```

新电脑克隆到名为 `pokedex` 的目录，配置 `.env` 后，在仓库根目录恢复。先确保目标数据库是新建且可覆盖；**`pg_restore --clean` 会删除目标库中已有的同名对象**。恢复媒体前确认目标卷为空。下列操作是未来迁机步骤，本次编写文档时未执行。

```powershell
$backupDir = 'D:\pokedex-transfer'
docker compose -p pokedex up -d db
docker cp "$backupDir\pokedex.dump" pokedex-db-1:/tmp/pokedex.dump
docker compose -p pokedex exec -T db sh -c 'pg_restore --clean --if-exists --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/pokedex.dump'
docker volume create pokedex_pokedex_media
docker run --rm -v pokedex_pokedex_media:/target -v "${backupDir}:/backup:ro" alpine:3.20 tar -C /target -xf /backup/media.tar
docker compose -p pokedex up -d --build api web caddy
```

恢复后核对数据库和媒体卷，再访问站点。若迁移前恢复的是当前旧数据库，其 `version_sprite` 表已存在而 `alembic_version` 仍在 `0001_initial_schema`；新版 API 启动迁移后应核对标记变成 `0002_version_sprites`。若恢复失败，不要运行重新采集来掩盖问题，先查看备份与容器日志。

### 可选：通过 Docker Hub 在线搬运卷

普通的 `docker push` / `docker pull` 只搬运**镜像**，不会携带挂载的 PostgreSQL 或图片卷。[Docker 官方说明](https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/)明确要求卷数据单独备份。不过，Docker Desktop 的 **Volumes → 卷名 → Exports → Quick export → Registry** 可把卷内容导出为 Docker Hub 上的镜像；新电脑在 **Volumes → 卷名 → Import → Registry** 导入。详见 [Docker Desktop 卷导出／导入文档](https://docs.docker.com/desktop/use-desktop/volumes/)。

若选这个图形界面方法，分别处理 `pokedex_pokedex_postgres` 和 `pokedex_pokedex_media`，使用**私有** Docker Hub 仓库；数据库卷含现有数据，图片卷约 7.9 GB，上传／下载会耗时且需确认账号容量。先停止项目服务并确认无写入，导出后在新电脑**启动数据库前**导入到空的同名卷，再启动 `db api web caddy`。导入会替换目标卷已有内容；不要导入到已有重要数据的卷。原始数据库卷保留旧用户和密码，不能仅靠新 `.env` 修改它们；若要换新密码，使用上文的逻辑备份恢复方式。数据库跨机器迁移仍以 `pg_dump`／`pg_restore` 更便于核验；Docker Hub 导出卷可作为在线传输的备选，并应在新电脑验证数据与图片。

外部服务：PokéAPI 是未来同步的数据源；GitHub 保存公开源码；Docker 镜像仓库和 Python/npm 软件源只在拉镜像／安装依赖时使用。现有 Compose 没有配置云数据库、对象存储或公网域名；若以后要公网部署，域名、HTTPS、备份周期和可用资源尚待决定。
