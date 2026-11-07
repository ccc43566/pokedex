<script setup lang="ts">
import { useId } from 'vue'
import { isVisibleType, type PresentedType } from '~/utils/typePresentation'

const props = withDefaults(
  defineProps<{
    modelValue?: string
    types: PresentedType[]
    allLabel: string
    label: string
    allValue?: string
    valueKey?: 'id' | 'name'
    disabled?: boolean
    showIcon?: boolean
  }>(),
  { modelValue: '', allValue: '', valueKey: 'name' },
)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const { locale } = useI18n()
const route = useRoute()
const id = useId()
const trigger = ref<HTMLButtonElement | null>(null)
const panel = ref<HTMLElement | null>(null)
const opened = ref(false)
const active = ref(0)
const position = ref<Record<string, string>>({})
const visible = computed(() => props.types.filter(isVisibleType))
const options = computed(() => [
  { value: props.allValue, type: null },
  ...visible.value.map((type) => ({ value: String(type[props.valueKey]), type })),
])
const selected = computed(() => options.value.find((o) => o.value === props.modelValue))
const caption = computed(
  () =>
    selected.value?.type?.localizedName ||
    (props.modelValue && props.modelValue !== props.allValue
      ? locale.value === 'zh-Hans'
        ? '未列出的属性筛选'
        : 'Unlisted type filter'
      : props.allLabel),
)
function reposition() {
  if (!opened.value || !trigger.value) return
  const box = trigger.value.getBoundingClientRect()
  const width = Math.min(Math.max(box.width, 240), 360, innerWidth - 24)
  const below = innerHeight - box.bottom - 12
  const above = box.top - 12
  const up = below < 220 && above > below
  const height = Math.max(80, Math.min(360, up ? above - 6 : below - 6))
  position.value = {
    width: `${width}px`,
    maxHeight: `${height}px`,
    left: `${Math.max(12, Math.min(box.left, innerWidth - width - 12))}px`,
    ...(up ? { bottom: `${innerHeight - box.top + 6}px` } : { top: `${box.bottom + 6}px` }),
  }
}
function close(focus = false) {
  opened.value = false
  if (focus) trigger.value?.focus({ preventScroll: true })
}
function focusAt(index: number) {
  active.value = (index + options.value.length) % options.value.length
  const element = panel.value?.querySelectorAll<HTMLButtonElement>('[role="option"]')[active.value]
  element?.focus({ preventScroll: true })
  element?.scrollIntoView({ block: 'nearest' })
}
async function open(last = false) {
  if (props.disabled) return
  opened.value = true
  reposition()
  await nextTick()
  const index = options.value.findIndex((o) => o.value === props.modelValue)
  focusAt(last && index <= 0 ? options.value.length - 1 : Math.max(0, index))
}
function choose(index: number) {
  emit('update:modelValue', options.value[index]!.value)
  close(true)
}
function triggerKey(event: KeyboardEvent) {
  if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(event.key)) {
    event.preventDefault()
    void open(event.key === 'ArrowUp')
  }
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    close(true)
  }
}
function optionKey(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    close(true)
    return
  }
  if (event.key === 'Tab') {
    close(true)
    return
  }
  let next: number | undefined
  if (['ArrowDown', 'ArrowRight'].includes(event.key)) next = active.value + 1
  if (['ArrowUp', 'ArrowLeft'].includes(event.key)) next = active.value - 1
  if (event.key === 'Home') next = 0
  if (event.key === 'End') next = options.value.length - 1
  if (next !== undefined) {
    event.preventDefault()
    focusAt(next)
  }
}
function outside(event: PointerEvent) {
  const target = event.target as Node
  if (!trigger.value?.contains(target) && !panel.value?.contains(target)) close()
}
watch(
  () => route.fullPath,
  () => close(),
)
watch(
  () => props.disabled,
  (value) => {
    if (value) close()
  },
)
onMounted(() => {
  window.addEventListener('pointerdown', outside)
  window.addEventListener('resize', reposition)
  window.addEventListener('scroll', reposition, true)
})
onUnmounted(() => {
  window.removeEventListener('pointerdown', outside)
  window.removeEventListener('resize', reposition)
  window.removeEventListener('scroll', reposition, true)
})
</script>

<template>
  <div class="type-select">
    <button
      :id="`${id}-trigger`"
      ref="trigger"
      class="type-select__trigger"
      type="button"
      role="combobox"
      :aria-label="label"
      :aria-describedby="`${id}-value`"
      aria-haspopup="listbox"
      :aria-expanded="opened"
      :aria-controls="`${id}-list`"
      :disabled="disabled"
      @click="opened ? close() : open()"
      @keydown="triggerKey"
    >
      <svg v-if="showIcon" class="type-select__icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" /></svg>
      <span :id="`${id}-value`"
        ><TypeBadge v-if="selected?.type" :type="selected.type" size="compact" /><span
          v-else
          class="type-select__neutral"
          >{{ caption }}</span
        ></span
      ><svg class="type-select__chevron" :class="{ 'is-open': opened }" viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m6 8 4 4 4-4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" /></svg>
    </button>
    <Teleport to="body">
      <div
        v-if="opened"
        :id="`${id}-list`"
        ref="panel"
        class="type-select__panel"
        :style="position"
        role="listbox"
        :aria-label="label"
        @keydown="optionKey"
      >
        <button
          v-for="(option, index) in options"
          :key="option.value"
          type="button"
          class="type-select__option"
          role="option"
          :aria-label="option.type?.localizedName || allLabel"
          :aria-selected="modelValue === option.value"
          :tabindex="active === index ? 0 : -1"
          @focus="active = index"
          @click="choose(index)"
        >
          <TypeBadge v-if="option.type" :type="option.type" size="compact" /><span
            v-else
            class="type-select__neutral"
            >{{ allLabel }}</span
          >
        </button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.type-select {
  min-width: 0;
}
.type-select__trigger {
  display: flex;
  width: 100%;
  min-height: 40px;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid #ccd7de;
  border-radius: 0.6rem;
  background: #f8fafc;
  font-size: 0.85rem;
  font-weight: 600;
  color: #1b2733;
}
.type-select__trigger:disabled {
  opacity: 0.5;
}
.type-select__icon { width:18px; height:18px; flex:none; }
.type-select__chevron { flex:none; width:18px; height:18px; color:#82949F; transition:transform .16s ease; }
.type-select__chevron.is-open { transform:rotate(180deg); }
@media (prefers-reduced-motion:reduce) { .type-select__chevron { transition:none; } }
.type-select__neutral {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 84px;
  min-height: 24px;
  font-size: 0.8rem;
  color: #667685;
}
.type-select__panel {
  position: fixed;
  z-index: 90;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  gap: 4px;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 8px;
  border: 1px solid #ccd7de;
  border-radius: 0.75rem;
  background: #fff;
  box-shadow: 0 12px 32px #1b273325;
}
.type-select__option {
  display: flex;
  min-width: 0;
  min-height: 40px;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 4px;
}
.type-select__option:hover {
  background: #edf2f7;
}
.type-select__option[aria-selected='true'] {
  border-color: #e84a4a;
  background: #fff5f4;
}
.type-select :focus-visible,
.type-select__option:focus-visible {
  outline: 3px solid #e84a4a;
  outline-offset: 1px;
}
</style>
