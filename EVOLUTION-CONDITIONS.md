# 进化条件中文说明与特殊分支

本轮不改变进化关系、形态匹配、记录、图鉴编号或导航。原始 `edge.methods` 全部保留，
API 另增同顺序的 `edge.methodExplanations`；抽屉与完整页共用 `EvolutionTree.vue`。

## 字典、中文释义和补充资料分开保存

- PokéAPI `evolution-trigger` 全部分页采集 18 条，`evolution-variable` 全部采集 4 条。
  复用 `source_record`、`catalog_dictionary`、`localized_name`、`localized_text`、
  `catalog_sync_entry`、`catalog_discovery_page` 和 `sync_run`，没有新增表或迁移。
- 原始 ID、英文标识、所有源语言名称／说明、原始 JSON、来源 URL、fetched_at、SHA-256
  都保留。简中／繁中／英文通过已有本地化表保存，其他语言完整留在原始 JSON 中。
- 这 22 条字典均未提供中文名称。项目中文释义集中维护在
  `apps/api/src/pokedex_api/data/evolution_explanations.json`，标明项目来源和规则版本，
  不写入上游字典的中文名称或覆盖其原文。API 优先已有上游中文名称，缺少时才用项目释义。
- 释义档案另存 `source_record.resource_type='project-evolution-glossary'`。
  经过核实的额外资料另存 `evolution-supplement`，有核实日期、来源、明确版本范围及
  `raw_pokeapi_fields=false`，不是冒充 PokéAPI 原字段。
- 招式、道具、属性等名称优先查询现有本地名称，再回退英文和可读标识；没有重复采集这些资源。

## 解释规则

`apps/api/src/pokedex_api/services/evolution_conditions.py` 是前后端共用的解释来源。

1. 每条真实连线的每一种途径单独解释。一个途径内的等级、道具、性别、招式、次数、
   地点、时间、同行、联机、天气等条件同时满足，不拆成可选项；不同途径仍分别展示。
2. 普通升级结合 min_level 输出“等级达到 N 后升级进化”。使用道具、携带道具、
   学会／使用招式和次数分别保留。0 值（如攻击=防御）不丢弃；已知不要求的 false
   仍在完整原字段中保留。未知字段（即使为 false）会标为待解释，不静默忽略。
3. 18 种触发方式的基础释义采用用户指定的项目中文词表，再结合具体字段形成文本。
   “交换或使用联系绳”的词表不代表联系绳在所有游戏通用，页面单独说明其版本限制。
4. 表达式只用受限 RPN 语法构造语法树；不使用 eval／exec、不调用来源中的代码，
   也不实际计算个体值。只识别已知的余数／位移比较结构、旋转方向／秒数和合取结构。
   有 token、长度和数值边界；未知算符、未声明变量、坏语法或不兼容定义都进入待解释。
5. 必须先取得变量原始定义，并验证 name、symbol、data_type、source 和关键描述。
   内部变量为 Pokémon 自身的 uint32；旋转变量为玩家输入。方向明确依据 variable/3
   的“0 for clockwise, 1 for counter-clockwise”，秒数依据 variable/4 的 seconds 定义。
   不根据“看起来像方向”或形态名字猜数值含义；定义缺失／改变时停止解释该表达式。
6. 比例只读取并验证源 `percentage_chance`（0～100），不从公式或变量名推算。
   土龙节节二节／三节、一家鼠四只／三只家庭分别显示约99%／1%，明确由个体内部值决定，
   不写成每次进化重新随机，也不承诺覆盖所有版本／特殊情况。学会强力钻、等级25、
   对战升级等其他原条件不会被比例取代。
7. 刺尾虫的 ruby-sapphire／PID 和 x-y／EC 记录保持分开，沿用各自源比例50%与
   is_default 标记。变量引入时间和途径引入版本均不能当作完整适用范围。
8. 霜奶仙按该形态真实方向、`<5`／`>=5`／`>=10` 秒、白天／夜晚／黄昏和携带糖饰
   组合展示；源未限定方向的虹色途径不补造方向。旋转不改写成概率。
9. 不认识的表达式显示“特殊条件待解释”；如源提供比例，只注明“数据源标注比例”，
   不据此宣称已理解其公式。原表达式、定义、比例和其他条件均保留，可展开核验。

来源／目标节点来自现有精确形态归组，不将当前形态的条件套到其他物种。特殊中文分支名
及必要的土居忍士例外集中在上述 JSON，注明依据，未按图片或名称合并任何记录。

## 土居忍士的两条独立关系

- #290→#291：源为 level-up、min_level=20；只显示该连线的升级条件。
- #290→#292：源为 shed；显示“土居忍士进化为铁面忍者时，蜕壳产生的额外宝可梦”。
  原始 shed 记录没有 min_level、队伍空位或精灵球字段，不把这些假装写回原数据。

独立核实补充仅限已记录范围：第三世代《红宝石／蓝宝石／绿宝石》《火红／叶绿》需要
空位，不需要额外普通精灵球；第四世代《钻石／珍珠／白金》《心金／魂银》需要空位和
一个普通精灵球并消耗该球。未外推到其他游戏或其他获得方式。这些补充只挂到 shed 连线。

依据：[Bulbapedia 进化资料](https://bulbapedia.bulbagarden.net/wiki/Shedinja_(Pok%C3%A9mon)#Evolution_data)、
[Smogon 球种指南](https://www.smogon.com/ingame/guides/special_ball#shedinja)。
上游定义见 [PokéAPI 进化章节](https://pokeapi.co/docs/v2/#evolution-section)。

## API 与页面

`methodExplanations[index]` 对应 `methods[index]`，主要字段：

- conditions／notes：面向用户的条件和限制说明；status 为 explained 或 partial。
- versionGroup／versionLabel／isDefault：原引入版本及默认标记，不用来过滤、重排或当作概率。
- triggerNameOrigin：upstream-translation、project-glossary、upstream-english 或 identifier。
- sources：明确区分项目释义和上游来源，保留 URL 和哈希；variables 中保留完整变量来源档案。
- supplements：有出处且限定版本的额外说明；unresolved：未能可靠解释的项目。

页面主区域显示条件、版本和释义来源。原字段／公式／变量定义放入折叠的核验区；
“默认标记”的提示明确其不是默认形态、唯一途径或概率。“引入版本”也明确不表示独占适用。
顶部选择器、底部形态栏、进化节点和浏览器历史仍使用原导航状态，未新增跳转规则。

## 维护和检查命令

仓库根目录使用现有 Python 3.13 虚拟环境，连接信息由本机包装器读取 `.env`：

```powershell
# 仅补齐两个进化字典；不请求 Pokemon／道具／招式／图片。
.\apps\api\.venv\Scripts\python.exe scripts/reference_data_db.py sync --evolution-dictionaries --report ..\migration-audit\evolution-dictionaries-sync.json

# 单个字典重取，仍限制在进化字典范围内。
.\apps\api\.venv\Scripts\python.exe scripts/reference_data_db.py sync --evolution-dictionaries --only evolution-variable:3 --refresh

# 保存项目释义与独立补充，绝不覆盖上游翻译。
.\apps\api\.venv\Scripts\python.exe scripts/sync_evolution_explanations.py

# 只读检查所有现有途径和未解释清单。
.\apps\api\.venv\Scripts\python.exe scripts/verify_evolution_conditions.py
```

改变解释语义时提升 JSON version，同步项目来源记录，并重启／重载开发 API，使缓存读取
新版本；不要因此重建 Docker 前端。raw JSON 是核验依据，不随自然语言模板改写。

本轮全部676条途径可解释，其中71条含表达式（8条内部值分支、63条旋转），待解释0。
测试覆盖未知公式、缺定义／中文／比例、版本差异、AND／OR、0／false、不同来源及形态导航。
最终测试、构建、预览和数据库比对证据见
`../migration-audit/EVOLUTION-CONDITIONS-RESULT-2026-10-29.md`。

限制：本轮没有补采地点、性格等无关资源；缺少本地中文的名称保持英文回退。
引入版本不是完整适用版本清单；独立补充只覆盖明确核实的第三／第四世代范围。
未来出现新表达式或变量定义变化，需要维护规则，不能保证自动解释。当前没有剩余待解释表达式。
