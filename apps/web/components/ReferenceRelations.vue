<script setup lang="ts">
import type { ReferenceKind, ReferenceFilters, RelationPage } from '~/types/references'
const props = defineProps<{
  kind: ReferenceKind
  recordId: number
  counts: Record<string, number>
}>()
const { tr } = useReferenceText()
const { locale } = useI18n()
const route = useRoute()
const router = useRouter()
const localePath = useLocalePath()
const { fetchApi } = usePokedexApi()
const labels: Record<string, [string, string]> = {
  holders: ['携带记录', 'Held item records'],
  learners: ['学习记录', 'Learnset records'],
  machines: ['招式机器', 'Machines'],
  evolutions: ['进化道具关联', 'Evolution item references'],
}
const stringQuery = (key: string) =>
  typeof route.query[key] === 'string' ? (route.query[key] as string) : ''
const selected = computed(() =>
  Object.hasOwn(props.counts, stringQuery('rel')) ? stringQuery('rel') : '',
)
const page = computed(() => Math.max(1, Number(stringQuery('rel_page')) || 1))
const versionGroup = computed({
  get: () => stringQuery('rel_vg'),
  set: (v) => setFilter('rel_vg', v),
})
const method = computed({
  get: () => stringQuery('rel_method'),
  set: (v) => setFilter('rel_method', v),
})
const version = computed({
  get: () => stringQuery('rel_version'),
  set: (v) => setFilter('rel_version', v),
})
function setFilter(key: string, value: string) {
  void router.push({
    path: route.path,
    query: { ...route.query, [key]: value || undefined, rel_page: undefined },
  })
}
function select(relation: string) {
  void router.push({
    path: route.path,
    query: {
      ...route.query,
      rel: relation,
      rel_page: undefined,
      rel_vg: undefined,
      rel_method: undefined,
      rel_version: undefined,
    },
  })
}
function changePage(next: number) {
  void router.push({ path: route.path, query: { ...route.query, rel_page: String(next) } })
}
const params = computed(() => ({
  locale: locale.value,
  page: page.value,
  version_group: /^\d+$/.test(versionGroup.value) ? versionGroup.value : undefined,
  method: /^\d+$/.test(method.value) ? method.value : undefined,
  version: /^\d+$/.test(version.value) ? version.value : undefined,
}))
const { data: filters } = await useAsyncData(
  () => `reference-filters-${props.kind}-${locale.value}`,
  () => fetchApi<ReferenceFilters>(`/${props.kind}/filters`, { params: { locale: locale.value } }),
)
const { data, pending, error, refresh } = await useAsyncData(
  () =>
    `relations-${props.kind}-${props.recordId}-${selected.value}-${JSON.stringify(params.value)}`,
  (_app, { signal }) =>
    selected.value
      ? fetchApi<RelationPage>(`/${props.kind}/${props.recordId}/${selected.value}`, {
          params: params.value,
          signal,
        })
      : Promise.resolve(null),
)
function related(kind: ReferenceKind, id: number) {
  return kind === props.kind
    ? {
        path: route.path,
        query: { ...route.query, detail: String(id), rel: undefined, rel_page: undefined },
      }
    : { path: localePath(`/${kind}`), query: { detail: String(id), from: route.fullPath } }
}
function pokemon(id: number, form?: string | null) {
  return {
    path: localePath(`/pokemon/${id}`),
    query: { from: route.fullPath, form: form || undefined },
  }
}
</script>

<template>
  <section class="ref-section">
    <h3>{{ tr('关联资料', 'Related data') }}</h3>
    <div class="ref-relation-tabs" :aria-label="tr('关联类型', 'Relation types')">
      <button
        v-for="(count, key) in counts"
        :key="key"
        class="ref-button"
        :class="{ 'ref-button--primary': selected === key }"
        :aria-pressed="selected === key"
        @click="select(key)"
      >
        {{ labels[key] ? tr(...labels[key]) : key }} ({{ count }})
      </button>
    </div>
    <p v-if="!selected" class="ref-note">
      {{
        tr(
          '选择一种关联查看，按需分页加载。计数为独立资料记录数，同一形态可有不同版本及学习方式。',
          'Choose a relation to load a page. Counts refer to individual records; a form may have multiple versions and learn methods.',
        )
      }}
    </p>
    <template v-else>
      <div class="ref-relation-filters">
        <label v-if="selected === 'learners' || selected === 'machines'" class="ref-select-label"
          >{{ tr('版本组', 'Version group')
          }}<select v-model="versionGroup" :aria-label="tr('版本组', 'Version group')">
            <option value="">{{ tr('全部版本组', 'All version groups') }}</option>
            <option v-for="v in filters?.['version-group']" :key="v.id" :value="String(v.id)">
              {{ v.localizedName }}
            </option>
          </select></label
        >
        <label v-if="selected === 'learners'" class="ref-select-label"
          >{{ tr('学习方式', 'Learn method')
          }}<select v-model="method" :aria-label="tr('学习方式', 'Learn method')">
            <option value="">{{ tr('全部方式', 'All methods') }}</option>
            <option v-for="v in filters?.['move-learn-method']" :key="v.id" :value="String(v.id)">
              {{ v.localizedName }}
            </option>
          </select></label
        >
        <label v-if="selected === 'holders'" class="ref-select-label"
          >{{ tr('游戏版本', 'Game version')
          }}<select v-model="version" :aria-label="tr('游戏版本', 'Game version')">
            <option value="">{{ tr('全部版本', 'All versions') }}</option>
            <option v-for="v in filters?.version" :key="v.id" :value="String(v.id)">
              {{ v.localizedName }}
            </option>
          </select></label
        >
      </div>
      <p v-if="pending" class="ref-note" role="status">{{ tr('加载中…', 'Loading…') }}</p>
      <p v-else-if="error" role="alert">
        {{ tr('关联加载失败', 'Could not load relations') }}
        <button class="ref-button" @click="refresh()">{{ tr('重试', 'Retry') }}</button>
      </p>
      <template v-else-if="data">
        <p class="ref-note" role="status">
          {{ data.total }} {{ tr('条关联记录', 'related records') }}
        </p>
        <div
          v-for="(row, i) in data.items"
          :key="`${row.id || row.pokemonId}:${i}`"
          class="ref-history-row"
        >
          <template v-if="row.pokemonId">
            <NuxtLink :to="pokemon(row.pokemonId)" class="ref-link"
              >#{{ row.displayNumber }}
              {{ row.displayName || `Pokémon #${row.pokemonId}` }}</NuxtLink
            >
            <p class="ref-note">
              {{ row.versionGroup?.localizedName || row.version?.localizedName
              }}<template v-if="row.method">
                · {{ row.method.localizedName }} · {{ tr('等级', 'Level') }} {{ row.level
                }}<template v-if="row.order != null">
                  · {{ tr('顺序', 'Order') }} {{ row.order }}</template
                ></template
              ><template v-if="row.rarity != null"> · rarity {{ row.rarity }}</template>
            </p>
          </template>
          <template v-else-if="selected === 'machines' && row.itemId && row.moveId">
            <p class="ref-note">{{ row.versionGroup?.localizedName }} · Machine #{{ row.id }}</p>
            <NuxtLink :to="related('items', row.itemId)" class="ref-link"
              >{{ row.itemName }} <small>#{{ row.itemId }}</small></NuxtLink
            ><span aria-hidden="true"> → </span
            ><NuxtLink :to="related('moves', row.moveId)" class="ref-link"
              >{{ row.moveName }} <small>#{{ row.moveId }}</small></NuxtLink
            >
          </template>
          <template v-else-if="selected === 'evolutions'">
            <h4>
              {{
                row.role === 'held_item'
                  ? tr('进化携带道具', 'Evolution held item')
                  : row.role === 'baby_trigger_item'
                    ? tr('孵化所需道具', 'Breeding item')
                    : tr('进化所用道具', 'Evolution item')
              }}
            </h4>
            <p v-if="row.source || row.target" class="ref-note">
              <template v-for="(node, n) in [row.source, row.target]" :key="n"
                ><span v-if="n === 1 && row.source" aria-hidden="true"> → </span
                ><NuxtLink
                  v-if="node?.pokemonId"
                  :to="pokemon(node.pokemonId, node.formKey)"
                  class="ref-link"
                  >#{{ node.displayNumber }} {{ node.displayName }}</NuxtLink
                ><span v-else-if="node">{{ node.displayName }}</span></template
              >
            </p>
            <details class="ref-note">
              <summary>{{ tr('来源索引', 'Source reference') }} · #{{ row.chainId }}</summary>
              {{ row.path }}
            </details>
          </template>
        </div>
        <p v-if="!data.total" class="ref-note">
          {{ tr('没有符合条件的本地关联记录', 'No matching local relation records') }}
        </p>
        <div v-if="data.totalPages > 1" class="ref-relation-pages">
          <button class="ref-button" :disabled="page <= 1" @click="changePage(page - 1)">
            {{ tr('上一页', 'Previous') }}</button
          ><span>{{ page }} / {{ data.totalPages }}</span
          ><button
            class="ref-button"
            :disabled="page >= data.totalPages"
            @click="changePage(page + 1)"
          >
            {{ tr('下一页', 'Next') }}
          </button>
        </div>
      </template>
    </template>
  </section>
</template>

<style scoped>
.ref-relation-tabs,
.ref-relation-pages {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}
.ref-relation-tabs button {
  font-size: 0.75rem;
}
.ref-relation-pages {
  justify-content: space-between;
  margin-top: 1rem;
  font-size: 0.8rem;
}
.ref-relation-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.8rem;
}
.ref-relation-filters label {
  min-width: 0;
  flex: 1;
}
</style>
