# 历代图片续传：2026-10-26

> 最终状态：2026-10-26 19:04（亚洲／上海）已完成，`report.json` 的 status 为 complete。待处理、失败、损坏均为 0；154,682 条非空图片关联全部已下载，489,918 条正常 null 保留。72,180 份物理图片文件全部通过 SHA-256／大小核对，数据库中每个内容哈希只有一个地址。最后补齐的 16 个 `.gif` 来源实际是有效 PNG/APNG，保留原字节及动画，按真实格式入库；浏览器已验证动画播放。Docker 前端未更新。

用户已授权恢复采集；Docker 前端须等用户另行明确下令才更新。本任务没有构建、重建、重启 Docker 服务，scheduler 和 media-sync 继续停止。

## 已执行的准备

- 已在仓库外 `..\migration-audit` 创建本次数据库逻辑备份及完整性核对记录。
- 续传前 38,796 个登记文件全部通过 SHA-256，未发现缺失或损坏。
- 全媒体库共 33,283 个唯一内容哈希，5,273 组哈希原先有多个文件路径。已统一数据库引用，重复旧文件改为同内容的硬链接别名，旧 URL 仍可访问。物理文件降为 33,283 份，约节省 335 MiB。
- 128 个 URL 的试采全部成功，复用 2 个已有哈希，新增文件内容约 422 MiB，对应补齐 259 条关联。
- 采集器新增 PostgreSQL 单实例锁、原子进度文件、逐批日志及空间保护。后端共 18 项测试、Ruff、mypy 已通过。

## 全量任务启动记录

2026-10-26 15:51（亚洲／上海），在现有 API 容器内通过 `docker compose exec -d` 启动独立任务。试采后尚有 46,074 个 URL、88,311 条关联需要处理，使用 32 并发。它不依赖聊天窗口继续打开；电脑与 Docker 需要保持运行。

采集脚本的当前源码已复制到 API 容器的 `/tmp/pokedex-collection`，没有替换 API 服务源码或构建镜像。

任务会处理现存 pending／download_failed／corrupt，正常 null 保留；不会刷新整套宝可梦资料。原始 PNG、GIF、WebP 格式不转换，每个 URL 在一轮内只请求一次，下载后按 SHA-256 复用全库已有内容。落盘采用临时文件后原子替换，分批提交数据库。

一轮之后若仍有失败，会再做最多两轮重试；每个 URL 的单次采集内部也有有限重试。任务最终会核对所有已下载文件的哈希、字节数，以及“每个哈希仅一个数据库地址”的约束，再写最终报告。无法获取的源文件会单独列明，状态为 needs_attention，不会冒充完成。

安全空间限制：媒体文件系统剩余空间低于 10 GiB，或者本轮新增物理内容达到 100 GiB 时，保存进度并停止。100 GiB 上限依据开始时宿主机至少约 124 GiB 剩余容量设置；保留了宿主机余量。若 Windows 同时有其他大量磁盘写入，仍应观察系统可用空间。

## 查看实时进度

仓库根目录：

```powershell
.\scripts\get-collection-status.ps1
```

也可直接访问本地 JSON：

- 实时批次进度：`http://localhost:8080/media/.collection/2026-10-26/progress.json`
- 总任务状态：`http://localhost:8080/media/.collection/2026-10-26/state.json`
- 任务日志：`http://localhost:8080/media/.collection/2026-10-26/job.log`
- 最终报告：`http://localhost:8080/media/.collection/2026-10-26/report.json`（结束后出现）。

时间戳文件使用 UTC；PowerShell 通常会按本机时区显示。progress.json 中计数是当前重试轮的计数，state.json 会保留各轮结果。日志和状态文件在媒体卷的 `.collection/2026-10-26`，属于任务记录，应与图片文件分开统计。

状态含义：running 为采集中；verifying 为下载结束后的完整性核对；complete 为队列清空且核对通过；needs_attention 为还有失败或完整性问题；failed 为异常中断。已提交的批次可断点续传。重启 Docker／电脑会停止当前进程，任务不会自行创建定时器重新启动。

## 收尾与前端验收

采集完成后，检查 report.json，确认 remainingUrls 为 0，完整性异常为 0；否则按失败清单继续处理。3000 开发预览重新打开详情即可读取新图片，不需要 JSON 预览快照。

Docker 前端保持用户目前使用的镜像，只有用户明确下达更新命令后才执行构建／替换。数据库数据与媒体文件增加会直接被现有 API 读取，这是本次采集的数据更新。

本次没有自动提交或推送代码。代码包括 `scripts/collect_version_media.py`（独立任务）、`scripts/run_version_sync.ps1`（前台、可限量续传）、`scripts/get-collection-status.ps1`（只读状态）、`apps/api/src/pokedex_api/sync/media_dedup.py`（验证／归并旧媒体）。
