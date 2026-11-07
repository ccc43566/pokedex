<script setup lang="ts">
import type { PaginatedPokemon, PokemonListItem } from '~/types/api'
const props = defineProps<{
  data: PaginatedPokemon | null
  pending: boolean
  failed: boolean
  restoring?: boolean
  paused?: boolean
  placeholders?: PokemonListItem[]
  generation?: boolean
  animateEntry?: boolean
}>()
const emit = defineEmits<{ more: []; retry: [] }>()
const { t, locale } = useI18n()
const sentinel = ref<HTMLElement | null>(null)
const grid = ref<HTMLElement | null>(null)
const allItems = computed(() => [...(props.data?.items || []), ...(props.placeholders || [])])
const { cardStyle, cardLayoutKey, columns } = usePokemonCardViewport(grid, allItems)
const ready = ref(!props.generation)
const preparing = computed(() => props.generation && !ready.value && !props.failed)
const entering = ref(false)
const entryCount = computed(() => columns.value * 3)
const entryItems = computed(() => props.data?.items.slice(0, entryCount.value) || [])
const remainingItems = computed(() => props.data?.items.slice(entryCount.value) || [])
let revealFrame = 0
let revealing = false
let disposed = false
function reveal() {
  if (ready.value || revealing || props.pending || !props.data?.items.length) return
  revealing = true
  void nextTick().then(() => {
    if (disposed) return
    revealFrame = requestAnimationFrame(() => {
      revealFrame = requestAnimationFrame(() => {
        if (disposed) return
        entering.value = Boolean(
          props.animateEntry &&
          !props.restoring &&
          !window.matchMedia('(prefers-reduced-motion: reduce)').matches,
        )
        ready.value = true
      })
    })
  })
}
watch([() => props.pending, () => props.data?.items.length], reveal, { flush: 'post' })
let observer: IntersectionObserver | undefined
function observe() {
  observer?.disconnect()
  if (sentinel.value) observer?.observe(sentinel.value)
}
watch([sentinel, ready, () => props.pending, () => props.restoring, () => props.paused], observe, {
  flush: 'post',
})
onMounted(() => {
  reveal()
  observer = new IntersectionObserver(
    ([entry]) => {
      if (
        entry?.isIntersecting &&
        ready.value &&
        !props.pending &&
        !props.restoring &&
        !props.failed &&
        !props.paused
      )
        emit('more')
    },
    // Data is already prefetched; leave enough distance to mount several small
    // groups before the reader reaches them, without watching every scroll frame.
    { rootMargin: '640px 0px' },
  )
  observe()
})
onUnmounted(() => {
  disposed = true
  observer?.disconnect()
  cancelAnimationFrame(revealFrame)
})
</script>

<template>
  <div
    class="pokemon-batch-list"
    :class="{ 'pokemon-batch-list--preparing': preparing }"
    :aria-busy="pending"
  >
    <div
      v-if="data && !generation"
      class="mb-4 flex items-center justify-between gap-3 text-sm text-slate-500"
      aria-live="polite"
    >
      <p>{{ t('filters.results', { count: data.total }) }}</p>
      <p>
        {{
          data.hasNext
            ? t('filters.partialShown', { count: data.items.length, total: data.total })
            : t('filters.allShown')
        }}
      </p>
    </div>
    <div v-if="!data && !failed && !generation" class="pokemon-grid">
      <USkeleton v-for="item in 12" :key="item" class="h-48 rounded-[14px]" />
    </div>
    <div
      v-else-if="data?.items.length"
      ref="grid"
      class="pokemon-grid"
      :style="{ visibility: ready ? undefined : 'hidden' }"
      :data-ready="ready"
    >
      <div
        class="pokemon-entry-group"
        :class="{ 'pokemon-entry-group--enter': entering }"
        @animationend.self="entering = false"
        @animationcancel.self="entering = false"
      >
        <PokemonCard
          v-for="(pokemon, index) in entryItems"
          :key="pokemon.id"
          v-memo="[pokemon, cardLayoutKey(pokemon.id)]"
          :pokemon="pokemon"
          :priority="index < Math.min(entryCount, 12)"
          :style="cardStyle(pokemon.id)"
        />
      </div>
      <PokemonCard
        v-for="pokemon in remainingItems"
        :key="pokemon.id"
        v-memo="[pokemon, cardLayoutKey(pokemon.id)]"
        :pokemon="pokemon"
        :style="cardStyle(pokemon.id)"
      />
      <PokemonCardPlaceholder
        v-for="pokemon in placeholders"
        :key="`pending-${pokemon.id}`"
        :pokemon="pokemon"
      />
    </div>
    <UAlert v-else-if="data && !failed" color="neutral" variant="soft" :title="t('common.empty')" />
    <div v-if="failed" class="mt-5 flex items-center gap-3" role="alert">
      <p class="text-sm">{{ t('common.error') }}</p>
      <UButton @click="emit('retry')">{{ t('common.retry') }}</UButton>
    </div>
    <div
      v-else-if="data?.hasNext"
      ref="sentinel"
      class="pokemon-batch-more"
      :style="{ visibility: ready ? undefined : 'hidden' }"
    >
      <UButton color="neutral" variant="soft" :disabled="pending" @click="emit('more')">{{
        pending ? t('common.loading') : locale === 'zh-Hans' ? '加载更多' : 'Load more'
      }}</UButton>
    </div>
  </div>
</template>

<style scoped>
.pokemon-batch-list {
  position: relative;
}
.pokemon-batch-list--preparing {
  padding-block: 0;
}
.pokemon-batch-list--preparing > .pokemon-grid,
.pokemon-batch-list--preparing > .pokemon-batch-more {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  visibility: hidden;
}
.pokemon-entry-group {
  display: grid;
  grid-column: 1 / -1;
  grid-template-columns: subgrid;
  gap: inherit;
  align-items: stretch;
}
.pokemon-entry-group--enter {
  animation: pokemon-entry 180ms cubic-bezier(0.16, 1, 0.3, 1) both;
}
@supports not (grid-template-columns: subgrid) {
  .pokemon-entry-group {
    display: contents;
  }
  .pokemon-entry-group--enter {
    animation: none;
  }
}
@keyframes pokemon-entry {
  from {
    transform: translateY(-8px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}
@media (prefers-reduced-motion: reduce) {
  .pokemon-entry-group--enter {
    animation: none;
  }
}
.pokemon-batch-more {
  display: flex;
  justify-content: center;
  padding-block: 24px 12px;
  min-height: 64px;
}
</style>
