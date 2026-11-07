# 本机独立开发环境

项目位置：`D:\Documents\ChatGPT\Pokedex\pokedex`。

## 已有 GitHub 仓库

本地 `main` 已跟踪 `origin/main`，远端为 `https://github.com/ccc43566/pokedex.git`。迁入的代码与接入时远端提交 `24c5f66` 一致。接入没有覆盖工作区或向 GitHub 推送。

日常核对：

```powershell
git status
git remote -v
git log -5 --oneline
git -c http.sslBackend=openssl fetch origin
```

本机 Git 的 schannel 方式连接 GitHub 时出现凭据错误；上述单次 `-c` 使用 OpenSSL，保留 TLS 证书校验，不修改全局 Git 配置。如果自己的终端正常，可以直接 `git fetch origin`。

提交和推送是另外的步骤：检查 `git diff`，选择需要提交的文件，`git add <文件>`、`git commit -m "说明"`，再 `git push origin main`。推送需要 GitHub 写入权限；本次未验证推送凭据。`.env`、`.tools`、`.venv`、node_modules 和媒体卷不提交。

## 环境范围

| 位置 | 内容 |
| --- | --- |
| `.tools/node` | 从本机 Node 24 复制的独立运行时，不修改系统 Node。 |
| `.tools/corepack`、`.tools/corepack-cache` | 项目私有 Corepack 和 `packageManager` 指定的 pnpm 11.19.0。 |
| `.tools/pnpm-store`、`.tools/npm-cache` | 项目私有前端包缓存，覆盖本机的全局缓存位置。 |
| `.tools/python` | uv 安装的 Python 3.13，安装时不注册系统 Python、不创建全局命令。 |
| `.tools/uv-cache` | 项目私有 Python 包缓存。 |
| `apps/api/.venv` | Python 3.13 API 依赖和测试工具。 |
| `apps/web/node_modules` | 根据 pnpm 锁文件安装的前端依赖。 |

Node 使用项目私有运行时、工具缓存和本地依赖来隔离；Python 使用 `.venv`。根目录 `.python-version` 固定 Python 3.13。以上生成文件均被 Git 忽略。

首次安装／重新准备环境，在仓库根目录运行：

```powershell
.\scripts\setup-dev.ps1
```

前置需要本机已有 Node 24（附 Corepack）和 uv，安装依赖需要联网。复制项目到其他机器后重新执行，不复制 `.tools`、`.venv` 或 node_modules。

## 每次打开终端

在仓库根目录**点调用**，让当前 PowerShell 使用本项目版本：

```powershell
. .\scripts\activate-dev.ps1
node --version
pnpm --version
python --version
```

关闭该终端即可离开环境。脚本不修改系统 PATH，也不修改其他项目的依赖。

## 热更新开发

本轮图鉴编号／形态调整需要新版 API。现有 8080 API 和 Docker 前端保持原样，使用下列独立预览流程：

```powershell
# 仓库根目录，启动／复用独立 API 预览，返回后再启动前端
.\scripts\start-api-preview.ps1
.\scripts\start-web-preview.ps1
```

API 预览监听 `127.0.0.1:8001`，复用现有 API 镜像及 Docker 数据库网络；源码和媒体均只读挂载，绕过镜像的迁移入口直接启动 Uvicorn。它不运行 Alembic 或同步，不构建镜像。3000 的 `/api/v1` 和 SSR 请求指向 8001；`/media` 继续指向 8080。

如果手动执行 `pnpm dev`，需先设置 `$env:POKEDEX_DEV_API_BACKEND = 'http://127.0.0.1:8001'`。未设置时仍默认读取原有 8080 API，无法看到新 API 的展示编号／归组字段。以下旧流程适用于仅编辑前端、继续使用旧 API 的情况。

保留已经运行的 Docker 8080 后端，使用独立环境启动前端：

```powershell
. .\scripts\activate-dev.ps1
cd apps/web
pnpm dev
```

打开 `http://127.0.0.1:3000/zh-Hans/pokemon`。3000 的 API 和媒体请求通过代理访问现有 8080 服务。停止开发预览按 Ctrl+C。

## 测试和检查

在单独的终端激活后，执行前端检查：

```powershell
. .\scripts\activate-dev.ps1
cd apps/web
pnpm typecheck
pnpm test
pnpm lint
pnpm build
$env:PLAYWRIGHT_USE_EDGE = '1'
pnpm e2e
```

后端：

```powershell
. .\scripts\activate-dev.ps1
cd apps/api
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen mypy src
```

后端单元测试使用 SQLite 临时数据库，不需要给宿主机开放 PostgreSQL。宿主机直接运行 API 服务则还需要单独准备数据库连接和媒体目录；当前日常开发继续使用 Docker API。

## Navicat 本机连接 PostgreSQL（2026-10-27）

Compose 的 db 服务将 `127.0.0.1:15432` 映射到容器 `5432`，仅绑定本机回环地址。

| Navicat 项目 | 值 |
| --- | --- |
| 连接类型 | PostgreSQL |
| 主机 | 127.0.0.1 |
| 端口 | 15432 |
| 数据库 | pokedex |
| 用户名 | pokedex |
| 密码 | 从项目根目录 `.env` 的 `POSTGRES_PASSWORD` 读取 |

已通过宿主机端口完成真实认证和只读查询。仅重建 db 容器，沿用原镜像和 `pokedex_pokedex_postgres` 卷；更新至健康约 7 秒。数据库记录计数保持不变，8080 原 API 和 8001 开发 API 均正常。原前端、API 容器未替换，媒体卷未改动，没有启动 scheduler 或执行同步。

## 属性标签链接修复

页面启用了语言前缀：中文属性页为 `/zh-Hans/types/grass`，英文为 `/en/types/grass`。原来的属性标签直接生成 `/types/grass`，缺少语言部分，会返回 404。`TypeBadge.vue` 现在通过现有的 `useLocalePath()` 生成链接，自动沿用当前语言。

源码修复首先在 3000 开发预览中生效；8080 Docker 网站需重建 web 服务后才会使用新代码。图片采集和 scheduler 继续保持暂停。

## 2026-10-26 实测结果

独立环境已安装：Node 24.22.1、pnpm 11.19.0、Python 3.13.17。Python 运行路径指向 `apps/api/.venv`，Node、pnpm、包缓存均指向本项目 `.tools`。

| 检查 | 结果 |
| --- | --- |
| 后端 pytest | 15 项通过。 |
| 后端 Ruff | 通过。 |
| 后端 mypy | 24 个源码文件通过。 |
| 前端 typecheck | 通过。 |
| 前端 Vitest | 2 个文件、7 项测试通过。 |
| 前端 ESLint | 0 错误；`PokemonVersionGallery.vue` 有 2 条原有 void element 自闭合格式警告。 |
| 前端生产构建 | 通过；有现有大分块和依赖包导出格式弃用警告。 |
| Playwright E2E | 桌面／移动端共 8 项通过，0 跳过、0 失败、0 flaky。 |
| 属性链接专项浏览器检查 | 中英文分别跳到 `/zh-Hans/types/grass`、`/en/types/grass`，页面标题分别为“草”和“Grass”；没有页面脚本错误或 HTTP 错误。 |
| 3000 开发代理 | health、历代图片 API、普通图片请求均返回 200。 |

本次未修改依赖锁文件，未提交或推送代码，未重建 Docker 服务。开发服务已启动；若终端或电脑重启，按本文的热更新开发步骤重新启动。
