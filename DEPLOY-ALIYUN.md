# 部署到阿里云 ECS 操作手册

面向第一次部署的人。跟着顺序做，每条命令都可以直接复制。

---

## 0. 先搞清楚要传什么

这个项目由 4 个容器组成，真正需要搬到服务器的东西只有三样：

| 内容 | 大小 | 说明 |
| --- | --- | --- |
| 代码 | 约 45MB | 已推到 GitHub，服务器 `git clone` 就能拿到，不用手动传 |
| 数据库 `pokedex.dump` | 48MB | 必须传。恢复后网站才有宝可梦数据 |
| 核心图片 `media-core.tar` | 380MB | 必须传。宝可梦立绘、形态图 |
| 历史图鉴 `media-version-sprites.tar` | 24.4GB | **可选**。各世代游戏原版像素图，先不要传 |

**镜像不用传。** 服务器上会从源代码重新构建（几百 MB），比传镜像包可靠。

### 关于那 24.4GB 的历史图鉴

你的服务器系统盘只有 **40GB**，账是这样的：

```
系统 + Docker 引擎         约 4GB
构建缓存和镜像             约 6GB
数据库                     约 1.2GB
核心图片                   0.4GB
历史图鉴图片              24.4GB   ← 放进来就爆了
--------------------------------
合计                      约 36GB / 40GB
```

所以**第一次部署不要传历史图鉴**。网站能正常用，只有宝可梦详情页的「历史版本图鉴」区块缩略图会缺失（显示空白）。等以后把系统盘扩到 100GB（阿里云控制台在线扩容，不停机，约 20 元/月），再执行一次解压即可补齐。

---

## 1. 开放端口（最容易卡住的一步）

阿里云默认只开 22 端口，3000 端口是关着的，不开的话浏览器永远连不上。

1. 控制台 → 云服务器 ECS → 实例 → 点进你的实例 `i-bp1dmnysh83ha3ae4s8wZ`
2. 上方标签页点 **安全组** → 点安全组 ID 那一行右侧的 **配置规则**
3. **入方向** 标签 → 右上角 **手动添加**
4. 填：

| 字段 | 值 |
| --- | --- |
| 目的 | `3000/3000` |
| 源 | `0.0.0.0/0` |
| 描述 | pokedex-web |

5. 保存

> 端口为什么是 3000 不是 80？因为大陆服务器用未备案域名/IP 访问 80 端口容易被拦，3000 是干净的。以后备案了域名，再把 `APP_PORT` 改成 80 即可。

---

## 2. 连上服务器

不需要装任何工具，用阿里云自带的网页终端：

1. 实例页面 → 右上角 **远程连接**
2. 选 **Workbench 远程连接** → 立即登录
3. 看到 `root@iZbp1dmnysh83ha3ae4s8wZ:~#` 就成功了

先装 git 和常用工具：

```bash
dnf install -y git tar curl
```

---

## 3. 拉代码

```bash
mkdir -p /opt && cd /opt
git clone https://github.com/ccc43566/pokedex.git
cd /opt/pokedex
```

如果 `git clone` 卡住或很慢（大陆访问 GitHub 常见），改用国内镜像：

```bash
cd /opt
git clone https://ghfast.top/https://github.com/ccc43566/pokedex.git
cd /opt/pokedex
```

拉完确认代码是新的（应该能看到 `deploy/` 目录）：

```bash
ls deploy/
```

---

## 4. 上传数据文件（用 WinSCP，图形界面）

Workbench 网页上传大文件容易断，用 WinSCP 更稳，支持断点续传。

1. 下载安装 [WinSCP](https://winscp.net/eng/download.php)（免费）
2. 打开后新建站点：
   - 文件协议：`SFTP`
   - 主机名：`115.29.208.75`
   - 端口：`22`
   - 用户名：`root`
   - 密码：就是你在阿里云控制台「重置密码」设置的那个。忘了就回控制台重置一次（需要重启实例）
3. 登录后，左侧窗口进到 `D:\Documents\ChatGPT\Pokedex\_deploy`
4. 右侧窗口进到 `/opt/pokedex/data`
5. 把左边三个文件拖到右边：

```
pokedex.dump
media-core.tar
```

> 这两个文件合计 428MB。按家宽 20Mbps 上行算约 3 分钟，慢一点也不会超过 15 分钟。中途断了右键文件选「续传」。

如果你还想要历史图鉴，同一个目录下的 `media-version-sprites.tar`（24.4GB）也拖过去——**但先确认已经扩容磁盘**。

---

## 5. 一键部署

回到 Workbench（第 2 步的网页终端）：

```bash
cd /opt/pokedex
bash deploy/deploy.sh 115.29.208.75
```

脚本会自动完成：生成带随机密码的 `.env` → 构建镜像 → 启动数据库 → 恢复备份 → 解压图片 → 启动服务 → 健康检查。

首次执行大约 **8~20 分钟**（大头是下载基础镜像和构建 Nuxt）。

看到这段就成功了：

```
================ 部署完成 ================
访问地址: http://115.29.208.75:3000/zh-Hans
```

浏览器打开试试。

---

## 6. 如果卡住了

### 构建时卡在拉取镜像 / 报 `i/o timeout`、`connection refused`

大陆服务器拉 Docker Hub 和 ghcr.io 经常失败。按顺序试：

**① 配置阿里云镜像加速器**

控制台 → 容器镜像服务 ACR → 管理控制台 → 镜像工具 → 镜像加速器，复制你的专属地址，然后在服务器上：

```bash
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": ["把这里换成你的加速器地址"]
}
EOF
systemctl daemon-reload && systemctl restart docker
```

**② 如果 `ghcr.io/astral-sh/uv` 这个镜像仍然拉不下来**（它是 api 镜像的基础镜像），换成国内可达的基础镜像。把 `apps/api/Dockerfile` 第一行改成：

```dockerfile
FROM python:3.13-slim
```

然后在 `RUN uv sync --frozen --no-dev` 之前补一步安装 uv：

```dockerfile
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple uv && uv sync --frozen --no-dev
```

改完重新跑 `bash deploy/deploy.sh 115.29.208.75`。

### 构建到一半进程被杀 / `Killed`

2 核 4G 构建 Nuxt 内存不够。加 2GB 交换分区：

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
free -h
```

### 站点打不开

```bash
docker compose ps                  # 四个容器是否 Up
docker compose logs --tail=50 web  # 前端日志
docker compose logs --tail=50 api  # 后端日志
curl -I http://127.0.0.1:3000/zh-Hans
```

如果 `curl` 本地通、浏览器不通 → 一定是第 1 步的安全组没生效。

如果首页能开但宝可梦列表是空的 → 数据库没恢复成功：

```bash
docker compose exec db psql -U pokedex -d pokedex -c "select count(*) from pokemon;"
```

正常应该是 1351。如果是 0 或报错表不存在，见下面「重来一次」。

### 重来一次

```bash
cd /opt/pokedex
docker compose down          # 注意：不要加 -v，加了会删数据
docker compose up -d db
# 手动清空库再恢复
docker compose exec -T db psql -U pokedex -d pokedex -c "drop schema public cascade; create schema public;"
docker compose cp data/pokedex.dump db:/tmp/pokedex.dump
docker compose exec -T db sh -c 'pg_restore --no-owner --no-acl -U "$POSTGRES_USER" -d "$POSTGRES_DB" /tmp/pokedex.dump'
docker compose up -d api web caddy
```

---

## 7. 日常运维（背下来这几条就够）

```bash
cd /opt/pokedex

docker compose ps                      # 看状态
docker compose logs -f --tail=100 web  # 看日志，Ctrl+C 退出
docker compose restart api web caddy   # 重启
df -h                                  # 查磁盘，注意 / 的使用率
```

**改代码后更新网站：**

```bash
cd /opt/pokedex
git pull
docker compose build web api
docker compose up -d api web caddy
```

**备份数据库（建议每周一次）：**

```bash
cd /opt/pokedex
mkdir -p backups
docker compose exec db pg_dump -U pokedex -d pokedex --no-owner --no-acl -Fc \
  > backups/pokedex-$(date +%F).dump
```

---

## 8. 以后想做的事

**绑定域名 + HTTPS**：需要域名先在阿里云完成 ICP 备案（1~3 周，免费）。备案通过后把 `APP_PORT` 改成 80，把 `Caddyfile` 里的 `:80` 改成 `你的域名 { ... }`，Caddy 会自动申请并续期证书，不用手动配 SSL。

**补齐历史图鉴**：控制台把系统盘扩到 100GB → 服务器上 `growpart /dev/vda 1 && xfs_growfs /`（或 `resize2fs`）→ WinSCP 上传 `media-version-sprites.tar` 到 `data/` → `SKIP_VERSION_SPRITES=0 bash deploy/deploy.sh 115.29.208.75`。

**自动备份**：`crontab -e` 加一行，每天凌晨 4 点备份并保留 7 天。

**关于版权**：宝可梦名称和图片版权归任天堂 / Creatures / GAME FREAK 所有。个人学习自用没问题，**不要商用、不要投广告**。
