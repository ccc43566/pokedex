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

# ---------- 2. 准备镜像 ----------
step "2/6 准备镜像"
# 默认使用导入的镜像。服务器的网络拉不到 ghcr.io / PyPI，
# 在这里构建几乎必然卡死，必须显式 BUILD=1 才会尝试。
if [ "${BUILD:-0}" = "1" ]; then
  echo "BUILD=1，在服务器上构建 api / web（需要能访问 ghcr.io）"
  docker compose build api web
else
  echo "使用已导入的镜像（如需在服务器上构建，请加 BUILD=1）"
  for img in pokedex-api pokedex-web; do
    if ! docker image inspect "$img" >/dev/null 2>&1; then
      echo ""
      echo "找不到镜像 $img。请先导入："
      echo "  docker load -i /opt/pokedex/data/pokedex-images.tar"
      exit 1
    fi
    echo "  已有镜像 $img"
  done
fi

# ---------- 3. 启动数据库 ----------
step "3/6 启动数据库"
docker compose up -d db
echo -n "等待数据库就绪"
for i in $(seq 1 60); do
  if docker compose exec -T db sh -c 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
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
TABLE_EXISTS=$(docker compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "select to_regclass('"'"'public.pokemon'"'"') is not null"' \
  2>/dev/null | tr -d '[:space:]' || echo "f")

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
  echo "media 数据卷尚未创建，将由下面的解压步骤自动创建"
else
  echo "目标数据卷: $VOL_MEDIA"
fi

if [ -f "data/media-core.tar" ]; then
  # 用已经构建好的 api 镜像来解压，避免额外依赖外网镜像
  EXISTING=$(docker compose run --rm --no-deps --entrypoint sh api -c \
    'ls -A /app/media 2>/dev/null | wc -l' 2>/dev/null | tr -d '[:space:]' || echo 0)
  if [ "${EXISTING:-0}" -gt 0 ]; then
    echo "数据卷里已有文件，跳过核心图片解压"
  else
    echo "正在解压 data/media-core.tar（约 380MB）..."
    docker compose run --rm --no-deps -v "$ROOT/data:/backup:ro" api \
      tar -C /app/media -xf /backup/media-core.tar
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
    docker compose run --rm --no-deps -v "$ROOT/data:/backup:ro" api \
      tar -C /app/media -xf /backup/media-version-sprites.tar
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
