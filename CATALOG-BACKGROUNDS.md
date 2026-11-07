# 图鉴页面背景接入

2026-11-05：把 `UI/image/背景适配/网页背景适配清单-v2.json` 中实际完成的素材接入现有页头「背景」选择器。主页已有独立设计，本次只接入使用共享页头的图鉴、属性、道具、招式和详情页面。

## 使用方式

- 页头「背景」中按日间、夜间选择，共保留 2 个原有默认背景并新增 11 个插画选项。
- 日间新增：关都御三家、卡比兽、胖丁皮卡丘与伙伴、手写信、赤、绿、蓝。
- 夜间新增：精灵球剪影、像素皮卡丘、固拉多与盖欧卡、已上色的赤红与皮卡丘。
- 每张插画有独立的「背景淡化」滑块，范围 0–80%。日间使用浅色蒙层，夜间使用深色蒙层。推荐值一般为 12%，赤红与皮卡丘为 32%，原夜间 1 保持原有的 79–88% 渐变蒙层。「恢复推荐」只影响当前插画。
- 原有「卡片背景」透明度仍独立保留。背景淡化不会改动卡片透明度。
- 原有 cookie `pokedex-appearance-v1` 和旧卡片透明度迁移逻辑保留。日间、夜间分别记住背景与卡片透明度；淡化值按插画保存。

## 素材与适配

新增 11 张桌面图和 8 张手机图，共 19 份 WebP。选择器仅加载小缩略图，完整背景只加载当前选择的设备版本。

8 个手机专版：御三家、卡比兽、手写信、固拉多与盖欧卡、赤、绿、蓝、赤红与皮卡丘。其余 3 张在手机使用完整桌面图，不裁断主体。没有把未完成的手机图或桌面修订版登记为已完成；胖丁伙伴、手写信、像素皮卡丘仍使用可用的桌面 v1。

赤、绿、蓝导入的是已确认去除底部平台账号的 v2 网络版；已上色的赤红与皮卡丘已经纳入。

新素材使用 `contain`、底部对齐和从各自图片取样的补色。静态渐变仅柔化实际图片边界，不改变原图。通过素材宽高比计算渐变的覆盖范围，避免在不同比例屏幕上出现硬接缝。小于 768px 的窗口，或小于等于 1024px 的竖屏，优先使用手机专版。

## 加载与渲染

`components/CatalogWallpaper.vue` 是单个固定视口背景层，保持既有合成与包含设置。没有滚动监听、运行时模糊、视差或持续动画。静态蒙层与边界渐变仅在选择、窗口尺寸或淡化值变化时更新。

切换前先加载、异步解码；准备好后再替换旧图。快速连续选择由请求序号防止旧结果覆盖新选择。失败或超时退回基础颜色并在设置面板提示，不阻止页面操作。

本次没有修改宝可梦卡片骨架、列表布局、筛选逻辑、世代展开逻辑、详情导航、API 或数据库。切换背景不写入页面路由，不重建列表，不触发列表首批刷新。

## 文件

- `apps/web/utils/appearance.ts`：原有默认项、偏好验证、背景类型。
- `apps/web/utils/catalogBackgrounds.ts`：11 个已完成素材的网页登记表。
- `apps/web/components/CatalogWallpaper.vue`：设备选图、解码、加载回退、边缘柔化。
- `apps/web/components/SiteAppearanceControl.vue`：缩略图选择、面板内部滚动、淡化控制、键盘操作。
- `apps/web/composables/useAppearance.ts`：沿用原有 cookie，独立保存每张背景的淡化值。
- `apps/web/public/catalog-backgrounds/`：19 份新背景、原夜间 1 的优化 WebP 和 12 份缩略图。
- `scripts/import-catalog-backgrounds.cjs`：从已完成清单复制网络版素材并生成登记表；不会修改原图。

## 验证

类型检查：在 `apps/web` 执行 `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit -p tsconfig.json`。

单元检查：`node node_modules/vitest/vitest.mjs run tests/appearance.test.ts tests/pokemonListCache.test.ts tests/detailNavigation.test.ts`。

浏览器检查：设置 `PLAYWRIGHT_USE_EDGE=1` 后执行 `node node_modules/@playwright/test/cli.js test tests/e2e/catalog-backgrounds.spec.ts --project=chromium --reporter=line`。

浏览器用例覆盖 11 张插画在 1440px 与 393px 窗口中的加载、设备分图、卡片尺寸和 DOM 保持、无横向溢出、Esc 焦点返回、仅请求当前大图、手机设置面板高度、模式与语言切换后的保存、淡化与卡片透明度独立、网络失败、快速切换竞态，以及 4 倍 CPU 降速下滚动时背景层没有重绘。截图与报告放在工作区 `design/catalog-review/`。

限制：验证期间开发 API `127.0.0.1:8001` 的宝可梦列表返回 HTTP 500。背景浏览器测试从正常运行的只读 `127.0.0.1:8080` API 取得真实记录作为固定样本，并在浏览器请求层提供这些记录；不改动开发服务配置。结果证明背景接入的隔离行为，不代表当前开发 API 已恢复，也不保证真实整页在所有设备上达到特定帧率。
