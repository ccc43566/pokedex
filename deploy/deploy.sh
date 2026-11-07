#!/usr/bin/env bash
# Pokédex 阿里云 ECS 一键部署脚本
#
# 用法（在服务器上、仓库根目录执行）：
#   bash deploy/deploy.sh <公网IP或域名>
#
# 例：bash deploy/deploy.sh 115.29.208.75
#
# 脚本做的事：
#   1. 生成 .env（数据库随机密码、站点地址、端口）
#   2. 构建 api / web 镜像
#   3. 启动数据库并恢复 pokedex.dump
#   4. 解压图片包到 pokedex_media 数据卷
#   5. 启动 api / web / caddy（不启动 scheduler 和 media-sync）
#   6. 健康检查
#
# 可重复执行：数据库已有数据时会跳过恢复，.env 不会被覆盖。

set -euo pipefail

SITE_HOST="${1:-}"
if [ -z "$SITE_HOST" ]; then
  echo "用法: bash deploy/deploy.sh <公网IP或域名>"
  exit 1
fi

APP_PORT="${APP_PORT:-3000}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

step() { echo ""; echo "==== $* ===="; }

if ! command -v docker >/dev/null 2>&1; then
  echo "找不到 docker 命令。请先在服务器安装 Docker。"
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "找不到 docker compose 插件。"
  exit 1
fi

# ---------- 1. 生成 .env ----------
step "1/6 检查 .env"
if [ -f .env ]; then
  echo ".env 已存在，跳过生成（如需重置请先备份并删除它）"
else
  PW="$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')"
  cat > .env <<EOF
POSTGRES_DB=pokedex
POSTGRES_USER=pokedex
POSTGRES_PASSWORD=${PW}
DATABASE_URL=postgresql+asyncpg://pokedex:${PW}@db:5432/pokedex
POKEAPI_BASE_URL=https://pokeapi.co/api/v2
POKEAPI_USER_AGENT=pokedex-prod/1.0
SYNC_CONCURRENCY=4
MEDIA_ROOT=/app/media
MEDIA_PUBLIC_PATH=/media
APP_PORT=${APP_PORT}
NUXT_API_BASE=http://api:8000
NUXT_PUBLIC_API_BASE=/api
NUXT_PUBLIC_SITE_URL=http://${SITE_HOST}:${APP_PORT}
EOF
  chmod 600 .env
  echo "已生成 .env，数据库密码为随机值（保存在 .env 里，请自行备份）"
fi

# ---------- 2. 构建镜像 ----------
step "2/6 构建镜像（首次约 5-15 分钟）"
docker compose build

# ---------- 3. 启动数据库 ----------
step "3/6 启动数据库"
docker compose up -d db
echo -n "等待数据库就绪"
for i in $(seq 1 60); do
  if docker compose exec -T db pg_isready -U pokedex -d pokedex >/dev/null 2>&1; then
    echo " ... 就绪"
    break
  fi
  echo -n "."
  sleep 2
  if [ "$i" -eq 60 ]; then
    echo ""
    echo "数据库 120 秒内未就绪，请检查: docker compose logs db"
    exit 1
  fi
done

# ---------- 4. 恢复数据库 ----------
step "4/6 恢复数据库"
TABLE_EXISTS=$(docker compose exec -T db psql -U pokedex -d pokedex -tAc \
  "select to_regclass('public.pokemon') is not null" 2>/dev/null | tr -d '[:space:]' || echo "f")

if [ -f "data/pokedex.dump" ]; then
  if [ "$TABLE_EXISTS" = "t" ]; then
    echo "数据库里已有数据，跳过恢复"
  else
    echo "正在恢复 data/pokedex.dump ..."
    docker compose cp data/pokedex.dump db:/tmp/pokedex.dump
    docker compose exec -T db sh -c \
      'pg_restore --clean --if-exists --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/pokedex.dump'
    echo "数据库恢复完成"
  fi
else
  echo "警告：未找到 data/pokedex.dump，跳过数据库恢复（站点会是空库）"
fi

# ---------- 5. 解压图片 ----------
step "5/6 解压图片资源"
VOL_MEDIA="$(docker volume ls --format '{{.Name}}' | grep -E '_pokedex_media$' | head -1 || true)"
if [ -z "$VOL_MEDIA" ]; then
  echo "找不到 media 数据卷，请先执行: docker compose up -d db"
  exit 1
fi
echo "目标数据卷: $VOL_MEDIA"

if [ -f "data/media-core.tar" ]; then
  EXISTING=$(docker run --rm -v "$VOL_MEDIA:/m" alpine:3.20 sh -c 'ls /m 2>/dev/null | wc -l' 2>/dev/null || echo 0)
  if [ "${EXISTING:-0}" -gt 0 ]; then
    echo "数据卷里已有文件，跳过核心图片解压"
  else
    echo "正在解压 data/media-core.tar（约 380MB）..."
    docker run --rm -v "$VOL_MEDIA:/m" -v "$ROOT/data:/backup:ro" alpine:3.20 \
      tar -C /m -xf /backup/media-core.tar
    echo "核心图片解压完成"
  fi
else
  echo "警告：未找到 data/media-core.tar，跳过"
fi

if [ -f "data/media-version-sprites.tar" ]; then
  if [ "${SKIP_VERSION_SPRITES:-1}" = "1" ]; then
    echo "检测到 media-version-sprites.tar，但默认跳过（磁盘占用约 24GB）。"
    echo "需要历史图鉴时执行: SKIP_VERSION_SPRITES=0 bash deploy/deploy.sh $SITE_HOST"
  else
    echo "正在解压历史图鉴图片（24GB，耗时较长）..."
    docker run --rm -v "$VOL_MEDIA:/m" -v "$ROOT/data:/backup:ro" alpine:3.20 \
      tar -C /m -xf /backup/media-version-sprites.tar
    echo "历史图鉴图片解压完成"
  fi
fi

# ---------- 6. 启动应用 ----------
step "6/6 启动应用"
# 只启动这四个服务；不要用不带服务名的 up -d，
# 否则 media-sync 会立刻开始下载 24GB 图片。
docker compose up -d api web caddy

echo -n "等待站点响应"
for i in $(seq 1 60); do
  if curl -sf -o /dev/null "http://127.0.0.1:${APP_PORT}/zh-Hans"; then
    echo " ... 完成"
    break
  fi
  echo -n "."
  sleep 3
  if [ "$i" -eq 60 ]; then
    echo ""
    echo "站点 180 秒内未响应，请检查日志："
    echo "  docker compose logs --tail=50 api web caddy"
    exit 1
  fi
done

echo ""
echo "================ 部署完成 ================"
echo "访问地址: http://${SITE_HOST}:${APP_PORT}/zh-Hans"
echo ""
echo "常用命令（在 $ROOT 目录下）:"
echo "  查看状态: docker compose ps"
echo "  查看日志: docker compose logs -f --tail=100"
echo "  重启:     docker compose restart api web caddy"
echo "  停止:     docker compose stop"
echo "=========================================="
