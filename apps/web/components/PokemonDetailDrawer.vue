<script setup lang="ts">
import type { PokemonDetail } from '~/types/api'

const props = defineProps<{ id: string; returnTo: string }>()
const emit = defineEmits<{ close: [] }>()
const { t, locale } = useI18n()
const localePath = useLocalePath()
const { fetchApi } = usePokedexApi()
const detail = shallowRef<PokemonDetail | null>(null)
const pending = ref(true)
const failed = ref(false)
const isModal = ref(false)
const closeButton = ref<HTMLButtonElement | null>(null)
const panel = ref<HTMLElement | null>(null)
let requestId = 0
let mediaQuery: MediaQueryList | undefined
let previousOverflow = ''
let modalApplied = false

async function loadDetail() {
  const currentRequest = ++requestId
  detail.value = null
  pending.value = true
  failed.value = false
  try {
    const result = await fetchApi<PokemonDetail>(`/pokemon/${props.id}`, {
      params: { locale: locale.value },
    })
    if (currentRequest === requestId) detail.value = result
  } catch {
    if (currentRequest === requestId) failed.value = true
  } finally {
    if (currentRequest === requestId) pending.value = false
  }
}

function updateModal() {
  const nextModal = Boolean(mediaQuery?.matches)
  if (nextModal === modalApplied) {
    isModal.value = nextModal
    return
  }
  isModal.value = nextModal
  const main = document.querySelector('main')
  if (nextModal) {
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    main?.setAttribute('inert', '')
  } else {
    document.body.style.overflow = previousOverflow
    main?.removeAttribute('inert')
  }
  modalApplied = nextModal
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
  if (event.key !== 'Tab' || !isModal.value || !panel.value) return
  const elements = [
    ...panel.value.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ]
  if (!elements.length) return
  const first = elements[0]!
  const last = elements[elements.length - 1]!
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(
  [() => props.id, locale],
  () => {
    if (import.meta.client) void loadDetail()
  },
  { immediate: true },
)

onMounted(() => {
  mediaQuery = window.matchMedia('(max-width: 1199px)')
  updateModal()
  mediaQuery.addEventListener('change', updateModal)
  window.addEventListener('keydown', handleKeydown)
  nextTick(() => closeButton.value?.focus())
})

onUnmounted(() => {
  requestId++
  mediaQuery?.removeEventListener('change', updateModal)
  window.removeEventListener('keydown', handleKeydown)
  if (modalApplied) {
    document.body.style.overflow = previousOverflow
    document.querySelector('main')?.removeAttribute('inert')
  }
  const card = document.querySelector<HTMLElement>(`[data-pokemon-id="${props.id}"]`)
  card?.focus()
})
</script>

<template>
  <div class="detail-drawer__backdrop" @click="emit('close')" />
  <aside
    ref="panel"
    class="detail-drawer"
    role="dialog"
    :aria-modal="isModal ? 'true' : undefined"
    :aria-label="detail?.localizedName || t('pokemon.description')"
  >
    <div class="detail-drawer__toolbar">
      <button
        ref="closeButton"
        class="detail-drawer__close"
        type="button"
        :aria-label="t('pokemon.close')"
        @click="emit('close')"
      >
        <span aria-hidden="true">×</span>
        {{ t('pokemon.close') }}
      </button>
      <NuxtLink
        :to="localePath({ path: `/pokemon/${id}`, query: { from: returnTo } })"
        class="detail-drawer__full"
      >
        {{ t('pokemon.fullPage') }}
      </NuxtLink>
    </div>
    <div class="detail-drawer__body">
      <div v-if="pending" class="space-y-3 p-4">
        <USkeleton class="h-56 rounded-xl" />
        <USkeleton class="h-40 rounded-xl" />
        <USkeleton class="h-48 rounded-xl" />
      </div>
      <div v-else-if="failed" class="p-4">
        <UAlert color="error" variant="soft" :title="t('common.error')" />
        <UButton class="mt-3" @click="loadDetail">{{ t('common.retry') }}</UButton>
      </div>
      <PokemonDetailContent v-else-if="detail" :pokemon="detail" compact />
    </div>
  </aside>
</template>

<style scoped>
.detail-drawer {
  position: fixed;
  z-index: 60;
  top: 0;
  right: 0;
  display: flex;
  width: 440px;
  max-width: 100vw;
  height: 100dvh;
  flex-direction: column;
  border-left: 1px solid #ccd7de;
  background: #f2f6f8;
  box-shadow: -8px 0 28px rgb(27 39 51 / 8%);
}
.detail-drawer__toolbar {
  display: flex;
  min-height: 4.25rem;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  border-bottom: 1px solid #ccd7de;
  background: #fff;
  padding: 0.5rem 1rem;
}
.detail-drawer__close {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  border-radius: 0.4rem;
  padding: 0.4rem 0.5rem;
  font-size: 0.9rem;
  font-weight: 700;
}
.detail-drawer__close span {
  font-size: 1.5rem;
  line-height: 1;
}
.detail-drawer__close:hover,
.detail-drawer__full:hover {
  color: #e84a4a;
}
.detail-drawer__close:focus-visible,
.detail-drawer__full:focus-visible {
  outline: 3px solid #e84a4a;
  outline-offset: 2px;
}
.detail-drawer__full {
  color: #667685;
  font-size: 0.8rem;
  font-weight: 650;
}
.detail-drawer__body {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 0.75rem;
}
.detail-drawer__backdrop {
  display: none;
}
@media (max-width: 1199px) {
  .detail-drawer__backdrop {
    position: fixed;
    z-index: 59;
    inset: 0;
    display: block;
    background: rgb(27 39 51 / 35%);
  }
}
@media (max-width: 767px) {
  .detail-drawer {
    width: 100vw;
    border-left: 0;
  }
}
@media (prefers-reduced-motion: no-preference) {
  .detail-drawer {
    animation: drawer-in 180ms ease-out;
  }
  @keyframes drawer-in {
    from {
      transform: translateX(16px);
      opacity: 0.7;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }
}
</style>
