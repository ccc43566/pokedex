<script setup lang="ts">
import type { ReferenceDetail, ReferenceKind } from '~/types/references'
import { isVisibleType } from '~/utils/typePresentation'
import { readableIdentifier } from '~/utils/references'
const props = defineProps<{ detail: ReferenceDetail; kind: ReferenceKind }>()
const { tr, value } = useReferenceText()
const isItem = computed(() => props.kind === 'items')
const record = computed(() => props.detail.record)
const fields = computed(() => props.detail.fields)
const selectedText = ref('')
const currentEffects = computed(() =>
  props.detail.texts
    .filter((t) => ['effect', 'short_effect'].includes(t.kind) && !t.version)
    .filter(
      (t, i, all) =>
        all.findIndex((other) => other.text === t.text && other.locale === t.locale) === i,
    ),
)
const histories = computed(() =>
  props.detail.texts.filter(
    (t) =>
      !currentEffects.value.includes(t) &&
      !(
        t.kind === 'short_effect' &&
        currentEffects.value.some((e) => e.text === t.text && e.version === t.version)
      ),
  ),
)
const historyOptions = computed(() => [
  ...new Map(
    histories.value.map((t) => [
      t.version || '',
      t.context?.localizedName || t.version || tr('未注明版本', 'Unspecified version'),
    ]),
  ).entries(),
])
const visibleTexts = computed(() =>
  histories.value.filter((t) => !selectedText.value || t.version === selectedText.value),
)
const numericFields = computed(
  () =>
    [
      [tr('威力', 'Power'), record.value.power],
      [tr('命中', 'Accuracy'), record.value.accuracy],
      ['PP', record.value.pp],
      [tr('优先度', 'Priority'), record.value.priority],
      [tr('效果概率（%）', 'Effect chance (%)'), fields.value.effectChance],
    ] as const,
)
const berryValues = computed(() => {
  const b = fields.value.berry
  return b
    ? ([
        [tr('每阶段生长（小时）', 'Growth per stage (hours)'), b.growthTime],
        [tr('第四世代最大收获量', 'Max harvest (Gen IV)'), b.maxHarvest],
        [tr('大小（毫米）', 'Size (mm)'), b.size],
        [tr('光滑度', 'Smoothness'), b.smoothness],
        [tr('土壤干燥度', 'Soil dryness'), b.soilDryness],
        [tr('自然之恩威力', 'Natural Gift power'), b.naturalGiftPower],
      ] as const)
    : []
})
const metaLabels: Record<string, [string, string]> = {
  drain: ['吸取／反作用（%）', 'Drain / recoil (%)'],
  healing: ['回复（%）', 'Healing (%)'],
  min_hits: ['最少命中次数', 'Minimum hits'],
  max_hits: ['最多命中次数', 'Maximum hits'],
  min_turns: ['最少持续回合', 'Minimum turns'],
  max_turns: ['最多持续回合', 'Maximum turns'],
  crit_rate: ['要害等级加成', 'Critical rate bonus'],
  stat_chance: ['能力变化概率（%）', 'Stat chance (%)'],
  flinch_chance: ['畏缩概率（%）', 'Flinch chance (%)'],
  ailment_chance: ['异常状态概率（%）', 'Ailment chance (%)'],
}
function effectText(text: string) {
  return fields.value.effectChance == null
    ? text
    : text.replaceAll('$effect_chance', String(fields.value.effectChance))
}
</script>

<template>
  <article class="reference-detail" :data-record-id="record.id" :data-kind="kind">
    <header class="ref-section ref-heading">
      <ItemImage
        v-if="isItem"
        :item-id="record.id"
        :src="record.imageUrl"
        :name="record.localizedName"
      />
      <div>
        <p class="ref-muted">
          {{ isItem ? tr('道具', 'Item') : tr('招式', 'Move') }} #{{ record.id }}
        </p>
        <h2>{{ record.localizedName }}</h2>
        <p class="ref-note">{{ record.name }}</p>
        <p v-if="record.nameLocale !== 'zh-Hans'" class="ref-note">
          {{ tr('名称回退：', 'Name fallback: ') }}{{ record.nameLocale }}
        </p>
      </div>
    </header>
    <section class="ref-section">
      <h3>{{ tr('基本资料', 'Overview') }}</h3>
      <dl class="ref-values">
        <template v-if="isItem"
          ><div>
            <dt>{{ tr('官方分类', 'Official category') }}</dt>
            <dd>{{ record.category?.localizedName || tr('未提供', 'Not provided') }}</dd>
          </div>
          <div>
            <dt>{{ tr('口袋', 'Pocket') }}</dt>
            <dd>{{ record.pocket?.localizedName || tr('未提供', 'Not provided') }}</dd>
          </div>
          <div>
            <dt>{{ tr('投掷威力', 'Fling power') }}</dt>
            <dd>{{ value(fields.flingPower) }}</dd>
          </div>
          <div v-if="fields.flingEffect">
            <dt>{{ tr('投掷效果', 'Fling effect') }}</dt>
            <dd>{{ fields.flingEffect.localizedName }}</dd>
          </div>
        </template>
        <template v-else>
          <div v-if="!record.type || isVisibleType(record.type)">
            <dt>{{ tr('属性', 'Type') }}</dt>
            <dd>
              <TypeBadge v-if="record.type" :type="record.type" link /><span v-else>{{
                tr('未提供', 'Not provided')
              }}</span>
            </dd>
          </div>
          <div>
            <dt>{{ tr('伤害类别', 'Damage class') }}</dt>
            <dd>{{ record.damageClass?.localizedName || tr('未提供', 'Not provided') }}</dd>
          </div>
          <div v-for="[label, n] in numericFields" :key="label">
            <dt>{{ label }}</dt>
            <dd>{{ value(n) }}</dd>
          </div>
          <div>
            <dt>{{ tr('目标', 'Target') }}</dt>
            <dd>{{ fields.target?.localizedName || tr('未提供', 'Not provided') }}</dd>
          </div>
          <div>
            <dt>{{ tr('引入世代', 'Introduced in') }}</dt>
            <dd>{{ record.generation?.localizedName || tr('未提供', 'Not provided') }}</dd>
          </div>
        </template>
      </dl>
      <p v-if="fields.attributes?.length" class="ref-note">
        {{ tr('属性标记：', 'Attributes: ')
        }}{{ fields.attributes.map((a) => a.localizedName).join(' · ') }}
      </p>
      <p v-if="!isItem" class="ref-note">
        {{
          tr(
            '空值表示上游未提供该数值，不等同于 0 或必中。引入世代不限定后续游戏中的可用性。',
            'A missing value does not mean zero or guaranteed accuracy. Introduction generation does not limit availability in later games.',
          )
        }}
      </p>
    </section>
    <section class="ref-section">
      <h3>{{ tr('效果', 'Effects') }}</h3>
      <template v-if="currentEffects.length"
        ><p v-for="(text, i) in currentEffects" :key="i" class="ref-text" :lang="text.locale">
          {{ effectText(text.text) }} <small class="ref-muted">[{{ text.locale }} · PokéAPI]</small>
        </p></template
      >
      <p v-else class="ref-muted">{{ tr('暂无效果说明', 'No effect description available') }}</p>
    </section>
    <ReferencePrices v-if="isItem" :prices="fields.prices || []" />
    <section v-if="fields.berry" class="ref-section">
      <h3>
        {{ tr('树果资料', 'Berry data') }} <small class="ref-muted">#{{ fields.berry.id }}</small>
      </h3>
      <dl class="ref-values">
        <div>
          <dt>{{ tr('硬度', 'Firmness') }}</dt>
          <dd>{{ fields.berry.firmness?.localizedName || tr('未提供', 'Not provided') }}</dd>
        </div>
        <div v-if="!fields.berry.naturalGiftType || isVisibleType(fields.berry.naturalGiftType)">
          <dt>{{ tr('自然之恩属性', 'Natural Gift type') }}</dt>
          <dd>
            <TypeBadge
              v-if="fields.berry.naturalGiftType"
              :type="fields.berry.naturalGiftType"
              link
            /><span v-else>{{ tr('未提供', 'Not provided') }}</span>
          </dd>
        </div>
        <div v-for="[label, n] in berryValues" :key="label">
          <dt>{{ label }}</dt>
          <dd>{{ value(n) }}</dd>
        </div>
        <div v-for="flavor in fields.berry.flavors" :key="flavor.flavor.id">
          <dt>{{ flavor.flavor.localizedName }}</dt>
          <dd>{{ flavor.potency }}</dd>
        </div>
      </dl>
      <p class="ref-note">
        {{
          tr(
            '此树果对应当前道具，名称和效果见上方。',
            'This Berry corresponds to the current item; see its name and effects above.',
          )
        }}
      </p>
    </section>
    <section v-if="!isItem" class="ref-section">
      <h3>{{ tr('能力变化与其他信息', 'Stat changes and other information') }}</h3>
      <p v-if="!fields.statChanges?.length" class="ref-muted">
        {{ tr('没有记录能力变化', 'No stat changes recorded') }}
      </p>
      <ul v-else>
        <li v-for="change in fields.statChanges" :key="change.stat.id">
          {{ change.stat.localizedName }} {{ change.change > 0 ? '+' : '' }}{{ change.change }}
        </li>
      </ul>
      <dl class="ref-values">
        <div v-if="fields.category">
          <dt>{{ tr('效果类别', 'Effect category') }}</dt>
          <dd>{{ fields.category.localizedName }}</dd>
        </div>
        <div v-if="fields.ailment">
          <dt>{{ tr('异常状态', 'Ailment') }}</dt>
          <dd>{{ fields.ailment.localizedName }}</dd>
        </div>
        <div v-for="(n, key) in fields.meta" :key="key">
          <dt>{{ metaLabels[key] ? tr(...metaLabels[key]) : readableIdentifier(key) }}</dt>
          <dd>{{ value(n) }}</dd>
        </div>
        <div v-if="fields.contestType">
          <dt>{{ tr('华丽大赛类别', 'Contest type') }}</dt>
          <dd>{{ fields.contestType.localizedName }}</dd>
        </div>
      </dl>
    </section>
    <section v-if="fields.pastValues?.length" class="ref-section">
      <h3>{{ tr('历代数值变化', 'Historical values') }}</h3>
      <p class="ref-note">
        {{
          tr(
            '按上游历史记录的版本组列出；空项保留为“未记录”，不填成 0。',
            'Grouped by the original historical version-group field. Empty fields remain unrecorded, never zero-filled.',
          )
        }}
      </p>
      <div v-for="(past, i) in fields.pastValues" :key="i" class="ref-history-row">
        <h4>{{ past.versionGroup?.localizedName || tr('未注明版本', 'Unspecified version') }}</h4>
        <dl class="ref-values">
          <div>
            <dt>{{ tr('威力', 'Power') }}</dt>
            <dd>{{ past.power ?? tr('未记录', 'Unrecorded') }}</dd>
          </div>
          <div>
            <dt>{{ tr('命中', 'Accuracy') }}</dt>
            <dd>{{ past.accuracy ?? tr('未记录', 'Unrecorded') }}</dd>
          </div>
          <div>
            <dt>PP</dt>
            <dd>{{ past.pp ?? tr('未记录', 'Unrecorded') }}</dd>
          </div>
          <div>
            <dt>{{ tr('效果概率（%）', 'Effect chance (%)') }}</dt>
            <dd>{{ past.effectChance ?? tr('未记录', 'Unrecorded') }}</dd>
          </div>
          <div v-if="past.type && isVisibleType(past.type)">
            <dt>{{ tr('属性', 'Type') }}</dt>
            <dd><TypeBadge :type="past.type" link /></dd>
          </div>
        </dl>
      </div>
    </section>
    <section class="ref-section">
      <h3>{{ tr('游戏说明与历史效果', 'Game descriptions and historical effects') }}</h3>
      <template v-if="histories.length"
        ><label class="ref-select-label"
          >{{ tr('说明版本', 'Description version')
          }}<select v-model="selectedText" :aria-label="tr('说明版本', 'Description version')">
            <option value="">{{ tr('全部已记录版本', 'All recorded versions') }}</option>
            <option v-for="[key, label] in historyOptions" :key="key" :value="key">
              {{ label }}
            </option>
          </select></label
        >
        <div
          v-for="(text, i) in visibleTexts"
          :key="`${text.version}:${text.kind}:${i}`"
          class="ref-history-row"
        >
          <h4>
            {{
              text.context?.localizedName || text.version || tr('未注明版本', 'Unspecified version')
            }}
            <small class="ref-muted"
              >{{
                text.kind === 'flavor'
                  ? tr('游戏说明', 'Description')
                  : tr('历史效果', 'Historical effect')
              }}
              · {{ text.locale }}</small
            >
          </h4>
          <p class="ref-text" :lang="text.locale">{{ text.text }}</p>
        </div>
      </template>
      <p v-else class="ref-muted">{{ tr('暂无说明资料', 'No descriptions available') }}</p>
    </section>
    <ReferenceRelations :kind="kind" :record-id="record.id" :counts="detail.relationCounts" />
    <details class="ref-section">
      <summary>{{ tr('来源与索引', 'Source and indices') }}</summary>
      <p class="ref-note">PokéAPI · {{ detail.source.fetchedAt }}</p>
      <a class="ref-link" :href="detail.source.url" target="_blank" rel="noopener noreferrer">{{
        detail.source.url
      }}</a>
      <p class="ref-note">SHA-256 {{ detail.source.hash }}</p>
      <template v-if="isItem"
        ><p class="ref-note">
          {{ tr('默认图片来源：', 'Default image source: ')
          }}{{ fields.imageSource || tr('未提供', 'Not provided') }}
        </p>
        <p v-if="fields.legacyCost != null" class="ref-note">
          {{
            tr(
              '原始 cost（未注明版本及货币，不作为游戏购买价）：',
              'Legacy cost (unspecified version/currency, not used as a game purchase price): ',
            )
          }}{{ fields.legacyCost }}
        </p>
        <p v-for="index in fields.gameIndices" :key="index.generation.id" class="ref-note">
          {{ index.generation.localizedName }} · Game index {{ index.index }}
        </p></template
      >
      <p class="ref-note">
        {{
          tr(
            '名称与说明使用上游中文，缺失时回退英文或原始标识；没有添加个人翻译。',
            'Names and descriptions use upstream Chinese, then English or the original identifier. No personal translations have been added.',
          )
        }}
      </p>
    </details>
  </article>
</template>

<style>
.reference-detail {
  min-width: 0;
  overflow-wrap: anywhere;
}
.reference-detail .ref-section {
  padding: 1.1rem;
  margin-bottom: 0.8rem;
  border: 1px solid var(--catalog-panel-line,#ccd7de);
  border-radius: 1.2rem;
  background: white;
}
.reference-detail .ref-heading {
  display: flex;
  gap: 1rem;
  align-items: center;
}
.reference-detail h2 {
  font-size: 1.65rem;
  font-weight: 850;
  line-height: 1.35;
}
.reference-detail h3 {
  margin-bottom: 0.8rem;
  font-size: 1.15rem;
  font-weight: 800;
}
.reference-detail h4 {
  font-weight: 700;
  font-size: 0.9rem;
}
.reference-detail .ref-values {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
  font-size: 0.9rem;
}
.reference-detail dt {
  color: var(--catalog-panel-muted,#667685);
  font-size: 0.75rem;
  line-height: 1.5;
}
.reference-detail dd {
  margin-top: 0.15rem;
  font-weight: 650;
}
.reference-detail .ref-muted {
  color: var(--catalog-panel-muted,#667685);
  font-size: 0.8rem;
}
.reference-detail .ref-note {
  color: var(--catalog-panel-muted,#667685);
  font-size: 0.75rem;
  line-height: 1.7;
  margin-top: 0.6rem;
}
.reference-detail .ref-text {
  margin-top: 0.5rem;
  font-size: 0.9rem;
  line-height: 1.8;
  white-space: pre-line;
}
.reference-detail .ref-history-row,
.reference-detail .ref-price-row {
  border-top: 1px solid #e1e9ee;
  padding-top: 0.8rem;
  margin-top: 0.8rem;
}
.reference-detail .ref-select-label {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.8rem;
}
.reference-detail select {
  max-width: 100%;
  min-height: 2.5rem;
  border: 1px solid var(--catalog-panel-line,#ccd7de);
  border-radius: 0.5rem;
  padding: 0.4rem;
  background: var(--catalog-panel-inset,#f8fafc);
}
.reference-detail .ref-link {
  color: #ac3434;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.reference-detail summary {
  cursor: pointer;
  font-weight: 700;
}
.reference-detail :is(a, button, select, summary):focus-visible {
  outline: 3px solid #e84a4a;
  outline-offset: 2px;
}
</style>
