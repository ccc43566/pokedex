<script setup lang="ts">
import { referenceListKey, referenceListQuery } from '~/utils/referenceListCache'
import type { ReferenceKind, ReferenceFilters } from '~/types/references'

const props = defineProps<{ kind: ReferenceKind }>()
const { locale } = useI18n()
const { tr, value } = useReferenceText()
const { fetchApi } = usePokedexApi()
const route = useRoute()
const router = useRouter()
const isItem = computed(() => props.kind === 'items')
const title = computed(() => (isItem.value ? tr('道具', 'Items') : tr('招式', 'Moves')))
useSeoMeta({ title: () => title.value })
const filterKeys = computed(() =>
  isItem.value ? ['pocket', 'category'] : ['type', 'damage_class', 'generation'],
)
const draft = reactive<Record<string, string>>({})
const queryString = (key: string) =>
  typeof route.query[key] === 'string' ? (route.query[key] as string) : ''
function syncDraft() {
  const applied = referenceListQuery(props.kind, locale.value, route.query)
  for (const key of ['q', 'sort', ...filterKeys.value])
    draft[key] = key === 'q' ? queryString('q').trim() : String(applied[key] ?? '')
}
watch(
  () => referenceListKey(props.kind, referenceListQuery(props.kind, locale.value, route.query)),
  syncDraft,
  { immediate: true },
)
const { data: filters } = await useAsyncData(
  () => `reference-filters-${props.kind}-${locale.value}`,
  () => fetchApi<ReferenceFilters>(`/${props.kind}/filters`, { params: { locale: locale.value } }),
)
const { state, retry, reload, whenReady, ready, hydrated } = useReferenceList(props.kind)
await ready
const data = computed(() => state.value)
const pending = computed(() => state.value.loading && !state.value.items.length)
const error = computed(() => state.value.error && !state.value.items.length)
useBrowsePosition(whenReady, 0)
function apply() {
  const query: Record<string, string | undefined> = { ...route.query } as Record<string, string>
  for (const key of ['q', 'sort', ...filterKeys.value]) query[key] = draft[key]?.trim() || undefined
  query.page = undefined
  void router.push({ path: route.path, query })
}
function clear() {
  void router.push({
    path: route.path,
    query: { detail: route.query.detail, from: route.query.from },
  })
}
function open(id: number) {
  const query = Object.fromEntries(
    Object.entries(route.query).filter(([key]) => key !== 'rel' && !key.startsWith('rel_')),
  )
  void router.push({ path: route.path, query: { ...query, detail: String(id) } })
}
const categories = computed(() =>
  (filters.value?.['item-category'] || []).filter(
    (c) => !draft.pocket || filters.value?.categoryPockets?.[String(c.id)] === Number(draft.pocket),
  ),
)
function changePocket() {
  draft.category = ''
}
</script>

<template>
  <section class="reference-browse mx-auto max-w-7xl px-4 py-8 lg:px-8" :data-list-ready="hydrated">
    <div class="mb-5">
      <p class="text-sm font-semibold text-red-500">Pokédex · {{ isItem ? 'Items' : 'Moves' }}</p>
      <h1 class="text-3xl font-black">{{ title }}</h1>
      <p class="mt-2 text-sm text-slate-500">
        {{
          isItem
            ? tr(
                '按官方分类浏览道具、精灵球与树果。',
                'Browse items, Poké Balls and Berries by official categories.',
              )
            : tr(
                '查询招式数值、历代资料及各形态的学习方式。',
                'Explore move values, history and learnsets for individual Pokémon forms.',
              )
        }}
      </p>
    </div>
    <form class="reference-filters" aria-label="筛选" @submit.prevent="apply">
      <label class="reference-search"
        ><span>{{ tr('名称或 ID', 'Name or ID') }}</span>
        <input
          v-model="draft.q"
          :readonly="!hydrated"
          type="search"
          :placeholder="tr('中文、英文或 ID', 'Name, identifier or ID')"
          maxlength="200"
        >
      </label>
      <template v-if="isItem">
        <label
          ><span>{{ tr('口袋', 'Pocket') }}</span
          ><select
            v-model="draft.pocket"
            :disabled="!hydrated"
            :aria-label="tr('口袋', 'Pocket')"
            @change="changePocket"
          >
            <option value="">{{ tr('全部口袋', 'All pockets') }}</option>
            <option v-for="p in filters?.['item-pocket']" :key="p.id" :value="String(p.id)">
              {{ p.localizedName }}
            </option>
          </select></label
        >
        <label
          ><span>{{ tr('分类', 'Category') }}</span
          ><select
            v-model="draft.category"
            :disabled="!hydrated"
            :aria-label="tr('分类', 'Category')"
          >
            <option value="">{{ tr('全部分类', 'All categories') }}</option>
            <option v-for="c in categories" :key="c.id" :value="String(c.id)">
              {{ c.localizedName }}
            </option>
          </select></label
        >
      </template>
      <template v-else>
        <label
          ><span>{{ tr('属性', 'Type') }}</span
          ><TypeSelect
            v-model="draft.type"
            :types="filters?.type || []"
            value-key="id"
            :label="tr('属性', 'Type')"
            :all-label="tr('全部属性', 'All types')"
            :disabled="!hydrated"
        /></label>
        <label
          ><span>{{ tr('伤害类别', 'Damage class') }}</span
          ><select
            v-model="draft.damage_class"
            :disabled="!hydrated"
            :aria-label="tr('伤害类别', 'Damage class')"
          >
            <option value="">{{ tr('全部类别', 'All classes') }}</option>
            <option v-for="p in filters?.['move-damage-class']" :key="p.id" :value="String(p.id)">
              {{ p.localizedName }}
            </option>
          </select></label
        >
        <label
          ><span>{{ tr('引入世代', 'Introduced in') }}</span
          ><select
            v-model="draft.generation"
            :disabled="!hydrated"
            :aria-label="tr('引入世代', 'Introduced in')"
          >
            <option value="">{{ tr('全部世代', 'All generations') }}</option>
            <option v-for="p in filters?.generation" :key="p.id" :value="String(p.id)">
              {{ p.localizedName }}
            </option>
          </select></label
        >
      </template>
      <label
        ><span>{{ tr('排序', 'Sort') }}</span
        ><select v-model="draft.sort" :disabled="!hydrated" :aria-label="tr('排序', 'Sort')">
          <option value="id">ID ↑</option>
          <option value="id_desc">ID ↓</option>
          <option value="name">{{ tr('名称', 'Name') }}</option>
          <option v-if="!isItem" value="power_desc">{{ tr('威力从高到低', 'Power ↓') }}</option>
          <option v-if="!isItem" value="priority_desc">
            {{ tr('优先度从高到低', 'Priority ↓') }}
          </option>
        </select></label
      >
      <div class="reference-actions">
        <button class="ref-button ref-button--primary" type="submit" :disabled="!hydrated">
          {{ tr('筛选', 'Apply') }}</button
        ><button class="ref-button" type="button" @click="clear">{{ tr('清除', 'Clear') }}</button>
      </div>
    </form>
    <p class="my-4 text-sm text-slate-500" role="status" aria-live="polite">
      {{
        pending
          ? tr('加载中…', 'Loading…')
          : `${data?.total || 0} ${tr('条记录', 'records')} · ${tr('已显示', 'Loaded')} ${state.items.length}`
      }}
    </p>
    <div v-if="error" role="alert">
      {{ tr('加载失败', 'Could not load data') }}
      <button class="ref-button" @click="retry()">{{ tr('重试', 'Retry') }}</button>
    </div>
    <div v-else-if="data" class="reference-grid" :class="{ 'reference-grid--items': isItem }">
      <button
        v-for="record in data.items"
        :key="`${kind}:${record.id}`"
        class="reference-card"
        :disabled="!hydrated"
        :class="{ 'reference-card--selected': queryString('detail') === String(record.id) }"
        :aria-label="`${title} #${record.id} ${record.localizedName}`"
        :aria-pressed="queryString('detail') === String(record.id)"
        @click="open(record.id)"
      >
        <span class="reference-card__id">#{{ record.id }}</span>
        <ItemImage
          v-if="isItem"
          :item-id="record.id"
          :src="record.imageUrl"
          :name="record.localizedName"
        />
        <strong>{{ record.localizedName }}</strong>
        <span v-if="isItem" class="reference-card__meta">{{
          record.category?.localizedName || record.pocket?.localizedName
        }}</span>
        <template v-else
          ><span class="flex flex-wrap justify-center gap-1"
            ><TypeBadge v-if="record.type" :type="record.type" size="compact" /><span
              v-else
              class="reference-card__meta"
              >{{ tr('未提供', 'Not provided') }}</span
            ><span class="reference-card__meta">{{ record.damageClass?.localizedName }}</span></span
          >
          <span class="reference-card__meta"
            >{{ tr('威力', 'Power') }} {{ value(record.power) }} · PP {{ value(record.pp) }}</span
          ></template
        >
      </button>
    </div>
    <p v-if="!pending && !error && !data?.items.length" class="py-10 text-center">
      {{ tr('没有符合条件的记录', 'No matching records') }}
    </p>
    <div class="reference-load-status" role="status" aria-live="polite">
      <p v-if="state.loading && state.items.length">
        {{ tr('后台继续加载', 'Loading remaining results') }} · {{ state.items.length }} /
        {{ state.total }}
      </p>
      <p v-else-if="state.error">
        {{ tr('加载失败，已保留成功加载的记录。', 'Loading failed; successful batches are kept.') }}
        <button class="ref-button" @click="retry">
          {{ tr('重试剩余批次', 'Retry remaining batches') }}
        </button>
      </p>
      <p v-else-if="state.complete">
        {{ tr('已显示全部', 'All results loaded') }} {{ state.items.length }} / {{ state.total }}
      </p>
      <button class="ref-button mt-3" @click="reload">
        {{ tr('重新加载列表', 'Reload list') }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.reference-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: end;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid #ccd7de;
  border-radius: 1.25rem;
  background: white;
}
.reference-filters label {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 130px;
  flex: 1;
  font-size: 0.8rem;
  font-weight: 650;
}
.reference-filters .reference-search {
  flex: 2;
  min-width: 200px;
}
.reference-filters input,
.reference-filters select {
  width: 100%;
  min-width: 0;
  border: 1px solid #ccd7de;
  border-radius: 0.6rem;
  min-height: 2.5rem;
  padding: 0.4rem 0.6rem;
  color: #1b2733;
  background: #f8fafc;
}
.reference-actions {
  display: flex;
  gap: 0.4rem;
}
.reference-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 0.75rem;
}
.reference-grid--items {
  grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
  gap: 0.6rem;
}
.reference-card {
  display: flex;
  position: relative;
  flex-direction: column;
  align-items: center;
  justify-content: start;
  gap: 0.4rem;
  min-width: 0;
  padding: 0.7rem;
  border: 1px solid #ccd7de;
  border-radius: 1rem;
  background: white;
  text-align: center;
  overflow-wrap: anywhere;
}
.reference-card strong {
  font-size: 0.95rem;
  line-height: 1.4;
}
.reference-card__id {
  align-self: start;
  font-size: 0.7rem;
  color: #667685;
  background: #f2f6f8;
  padding: 0.1rem 0.3rem;
  border-radius: 0.25rem;
}
.reference-card__meta {
  font-size: 0.72rem;
  line-height: 1.5;
  color: #667685;
}
.reference-card:hover {
  border-color: #e84a4a;
}
.reference-card--selected {
  border-color: #e84a4a;
  box-shadow: inset 3px 0 #e84a4a;
}
.reference-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}
@media (max-width: 450px) {
  .reference-grid--items {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.4rem;
  }
  .reference-grid {
    gap: 0.5rem;
  }
  .reference-card {
    padding: 0.5rem;
  }
  .reference-card strong {
    font-size: 0.85rem;
  }
}
</style>
