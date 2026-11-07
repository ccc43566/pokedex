# 日间 / 夜间与背景库

图鉴等内页顶部提供模式切换按钮和背景选择按钮。初次使用为日间；模式切换完全手动，不按时间或系统偏好自动切换。独立夜景首页保持原样。

- 日间 1：现有已确认的草野目录。
- 夜间 1：复用项目现有 `public/home/night/observatory-night.png` 观星庭院插画，叠加遮罩，以深蓝灰面板保证内容可读。
- 每种模式独立记录背景 ID 和卡片纸面不透明度。默认 / 推荐：日间 80%，夜间 88%。图鉴右下角的透明度控件保留，并自动显示当前模式的值与推荐档位。
- 旧版单独保存的卡片不透明度迁移为日间值；不改变图片、文字、类型标签的透明度，也不增加悬浮缩放。夜间卡片使用深色纸面混入少量草色，网格和环线降低对比。

## 配置与扩展

`apps/web/utils/appearance.ts` 的 `appearanceBackgrounds` 为背景注册表。新增日间 2、3、4 或夜间背景时：

1. 将图片放入 `apps/web/public/` 的对应目录。
2. 在注册表中添加唯一 `id`、`mode`、中英文名称与描述、`image` 路径、缩略图 CSS `preview`。
3. 背景选择器按模式自动分组，不需要修改面板结构。日间的无图草野样式继续保留；新日间图片和所有夜间图片均通过 `--catalog-wallpaper` 渲染并自动加对应模式的遮罩。

`useAppearance.ts` 负责版本化 cookie `pokedex-appearance-v1`。状态包含：

```json
{
  "mode": "day",
  "backgrounds": {"day":"day-1","night":"night-1"},
  "opacity": {"day":80,"night":88}
}
```

状态在服务端规范化并渲染当前模式，减少刷新时的明暗闪变；无效模式、失效背景 ID 与异常透明度会回退或钳制到合理范围。Cookie 有效期一年。

`catalog-night.css` 定义夜间语义颜色。HTML 的 `data-catalog-mode` 同时控制传送到 body 的下拉菜单，页面根节点的 `data-mode` / `data-background` 控制背景与正文。日间不改变现有布局；夜间不使用全页反色或降低原画亮度。

背景图片及遮罩由独立的固定视口层 `.catalog-wallpaper` 渲染，不在长页面上使用 `background-attachment:fixed`，避免滚动时重复栅格化。卡片保留懒加载图片，并使用局部布局 / 绘制隔离，而非逐张 `content-visibility:auto`，减少行进入视口引起的整页布局。性能记录见 `design/catalog-review/SCROLL-PERFORMANCE.md`。

详情、媒体图库和关联信息的固定浅色样式使用带日间原值回退的语义变量；夜间调整面板和文字颜色。

## 验证

`design/catalog-review/appearance-qa.cjs` 检查旧设置迁移、模式分别记忆、刷新与 SSR、背景选择、下拉菜单夜色、320/393/768/947/1440px 无横向溢出、详情、英文、首页独立样式。结果见 `appearance-qa.json`。另检查了无效设置 / 0% 不透明度的边界和夜间详情描述的颜色。

Vue TypeScript 检查通过。当前截图：`appearance-day-desktop.png`、`appearance-night-desktop.png`、`appearance-night-mobile.png`、`appearance-night-detail.png`。
