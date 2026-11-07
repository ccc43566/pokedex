<script setup lang="ts">
import { appearanceBackgrounds, type AppearanceMode } from '~/utils/appearance'
const props = defineProps<{
  mode: AppearanceMode
  backgroundId: string
  dimming?: number
  state?: 'loading' | 'ready' | 'error'
}>()
const emit = defineEmits<{
  'update:mode': [value: AppearanceMode]
  'update:background': [id: string]
  'update:dimming': [value: number]
}>()
const { locale } = useI18n()
const zh = computed(() => locale.value === 'zh-Hans')
const opened = ref(false),
  root = ref<HTMLElement | null>(null),
  trigger = ref<HTMLButtonElement | null>(null)
const id = useId()
const backgrounds = computed(() => appearanceBackgrounds.filter((b) => b.mode === props.mode))
const selected = computed(() => backgrounds.value.find((b) => b.id === props.backgroundId))
const recommendedDimming = computed(() => Math.round((selected.value?.overlay ?? 0.12) * 100))
function changeDimming(event: Event) {
  emit('update:dimming', Number((event.target as HTMLInputElement).value))
}
async function togglePanel() {
  opened.value = !opened.value
  if (opened.value) {
    await nextTick()
    root.value
      ?.querySelector<HTMLButtonElement>('.appearance-background[aria-pressed=true]')
      ?.focus()
  }
}
function close() {
  opened.value = false
  trigger.value?.focus()
}
function outside(e: PointerEvent) {
  if (!root.value?.contains(e.target as Node)) opened.value = false
}
onMounted(() => document.addEventListener('pointerdown', outside))
onBeforeUnmount(() => document.removeEventListener('pointerdown', outside))
</script>
<template>
  <div ref="root" class="appearance-control" @keydown.esc.stop.prevent="close">
    <button
      type="button"
      class="appearance-action appearance-toggle"
      :aria-label="
        zh
          ? mode === 'day'
            ? '切换到夜间模式'
            : '切换到日间模式'
          : mode === 'day'
            ? 'Switch to night mode'
            : 'Switch to day mode'
      "
      @click="emit('update:mode', mode === 'day' ? 'night' : 'day')"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path v-if="mode === 'day'" d="M20.5 13a8.5 8.5 0 0 1-9.5-9.5A8.5 8.5 0 1 0 20.5 13Z" />
        <template v-else>
          <circle cx="12" cy="12" r="4" />
          <path
            d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M19 5l-1.5 1.5m-11 11L5 19"
          />
        </template>
      </svg>
      <span>{{ zh ? (mode === 'day' ? '夜间' : '日间') : mode === 'day' ? 'Night' : 'Day' }}</span>
    </button>
    <button
      ref="trigger"
      type="button"
      class="appearance-action"
      :aria-label="zh ? '选择页面背景' : 'Choose page background'"
      :aria-expanded="opened"
      :aria-controls="`${id}-panel`"
      @click="togglePanel"
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <rect x="3" y="4" width="18" height="16" rx="3" />
        <circle cx="8" cy="9" r="1.5" />
        <path d="m3 17 5-5 4 4 4-6 5 7" /></svg
      ><span>{{ zh ? '背景' : 'Background' }}</span>
    </button>
    <div
      v-if="opened"
      :id="`${id}-panel`"
      class="appearance-panel"
      role="group"
      :aria-label="zh ? '页面背景设置' : 'Page background settings'"
    >
      <div class="appearance-panel-heading">
        <strong>{{ zh ? '页面外观' : 'Appearance' }}</strong
        ><button
          type="button"
          class="appearance-close"
          :aria-label="zh ? '关闭外观设置' : 'Close appearance settings'"
          @click="close"
        >
          ×
        </button>
      </div>
      <div
        class="appearance-mode-options"
        role="group"
        :aria-label="zh ? '显示模式' : 'Display mode'"
      >
        <button
          v-for="value in ['day', 'night'] as const"
          :key="value"
          type="button"
          :aria-pressed="mode === value"
          @click="emit('update:mode', value)"
        >
          {{ zh ? (value === 'day' ? '日间' : '夜间') : value === 'day' ? 'Day' : 'Night' }}
        </button>
      </div>
      <div class="appearance-backgrounds">
        <button
          v-for="item in backgrounds"
          :key="item.id"
          type="button"
          class="appearance-background"
          :aria-pressed="backgroundId === item.id"
          @click="emit('update:background', item.id)"
        >
          <span
            class="appearance-thumbnail"
            :style="item.thumbnail ? undefined : { background: item.preview }"
            ><img
              v-if="item.thumbnail"
              :src="item.thumbnail"
              alt=""
              width="240"
              height="135"
              loading="lazy"
              decoding="async" /></span
          ><span class="appearance-background-caption"
            ><strong>{{ zh ? item.name : item.en }}</strong
            ><small>{{ zh ? item.description : item.enDescription }}</small
            ><span v-if="backgroundId === item.id" aria-hidden="true">✓</span></span
          >
        </button>
      </div>
      <div v-if="selected?.image" class="appearance-dimming">
        <div class="appearance-dimming-heading">
          <label :for="`${id}-dimming`">{{ zh ? '背景淡化' : 'Background veil' }}</label>
          <output :for="`${id}-dimming`">{{ dimming ?? recommendedDimming }}%</output>
        </div>
        <input
          :id="`${id}-dimming`"
          type="range"
          min="0"
          max="80"
          step="1"
          :value="dimming ?? recommendedDimming"
          @input="changeDimming"
        />
        <button type="button" @click="emit('update:dimming', recommendedDimming)">
          {{ zh ? `恢复推荐 ${recommendedDimming}%` : `Recommended ${recommendedDimming}%` }}
        </button>
      </div>
      <p v-if="state === 'loading'" role="status">
        {{ zh ? '背景加载中…' : 'Loading background…' }}
      </p>
      <p v-else-if="state === 'error'" role="status">
        {{
          zh ? '背景加载失败，已显示基础底色。' : 'Background unavailable. Showing the base color.'
        }}
      </p>
      <p>
        {{
          zh
            ? '分别记住日间和夜间的背景与卡片透明度。'
            : 'Background and card opacity are remembered separately for each mode.'
        }}
      </p>
    </div>
  </div>
</template>
<style scoped>
.appearance-control {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
}
.appearance-action {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 34px;
  padding: 6px 9px;
  border: 1px solid var(--appearance-line, #d3dfd5);
  border-radius: 7px;
  background: var(--appearance-panel, #fff);
  color: var(--appearance-text, #3e6650);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.appearance-action svg {
  width: 17px;
  height: 17px;
  flex: none;
}
.appearance-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 12px);
  width: min(308px, calc(100vw - 28px));
  padding: 16px;
  background: var(--appearance-panel, #fff);
  color: var(--appearance-text, #294435);
  border: 1px solid var(--appearance-line, #d3dfd5);
  border-radius: 12px;
  box-shadow: 0 12px 36px #10201825;
  z-index: 70;
}
.appearance-panel-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 13px;
  font-size: 14px;
}
.appearance-close {
  padding: 1px 6px;
  font-size: 22px;
  color: var(--appearance-muted, #74877a);
  cursor: pointer;
}
.appearance-mode-options {
  display: flex;
  gap: 4px;
  padding: 3px;
  margin-bottom: 14px;
  background: var(--appearance-inset, #edf2ed);
  border-radius: 7px;
}
.appearance-mode-options button {
  flex: 1;
  padding: 7px;
  border-radius: 5px;
  font-size: 12px;
  color: var(--appearance-muted, #60756a);
  cursor: pointer;
}
.appearance-mode-options button[aria-pressed='true'] {
  background: var(--appearance-panel, #fff);
  color: var(--appearance-text, #294435);
  box-shadow: 0 1px 4px #10201810;
}
.appearance-background {
  display: block;
  width: 100%;
  border: 1px solid var(--appearance-line, #d3dfd5);
  border-radius: 8px;
  overflow: hidden;
  text-align: left;
  cursor: pointer;
}
.appearance-background[aria-pressed='true'] {
  border-color: var(--appearance-accent, #568465);
}
.appearance-thumbnail {
  display: block;
  height: 94px;
}
.appearance-background-caption {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px;
  font-size: 12px;
}
.appearance-background-caption small {
  font-size: 11px;
  color: var(--appearance-muted, #74877a);
}
.appearance-background-caption > span {
  margin-left: auto;
  color: var(--appearance-accent, #568465);
}
p {
  margin: 12px 0 0;
  font-size: 11px;
  line-height: 1.7;
  color: var(--appearance-muted, #74877a);
}
button:focus-visible {
  outline: 2px solid var(--appearance-accent, #568465);
  outline-offset: 3px;
}
@media (max-width: 1100px) {
  .appearance-action > span {
    display: none;
  }
  .appearance-action {
    width: 32px;
    padding: 6px;
  }
}
@media (max-width: 600px) {
  .appearance-panel {
    position: fixed;
    top: 62px;
    right: 12px;
  }
}
.appearance-panel {
  display: flex;
  flex-direction: column;
  max-height: min(640px, calc(100dvh - var(--dex-header-height, 68px) - 32px));
}
.appearance-backgrounds {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: max-content;
  align-content: start;
  gap: 8px;
  overflow-y: auto;
  overscroll-behavior: contain;
  min-height: 0;
  padding: 3px;
  scrollbar-width: thin;
}
.appearance-backgrounds:focus-within {
  scroll-behavior: auto;
}
.appearance-thumbnail {
  height: 72px;
  overflow: hidden;
}
.appearance-thumbnail img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: var(--appearance-inset, #edf2ed);
}
.appearance-background-caption {
  position: relative;
  display: block;
  padding: 8px;
  font-size: 12px;
}
.appearance-background-caption strong {
  display: block;
  padding-right: 12px;
  line-height: 1.4;
}
.appearance-background-caption small {
  display: block;
  margin-top: 3px;
  line-height: 1.4;
}
.appearance-background-caption > span {
  position: absolute;
  right: 7px;
  top: 7px;
}
.appearance-panel-heading,
.appearance-mode-options,
.appearance-dimming,
.appearance-panel > p {
  flex-shrink: 0;
}
.appearance-dimming {
  margin-top: 12px;
  font-size: 12px;
}
.appearance-dimming-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.appearance-dimming input {
  display: block;
  width: 100%;
  margin: 8px 0;
  accent-color: var(--appearance-accent, #568465);
}
.appearance-dimming button {
  padding: 3px 0;
  color: var(--appearance-muted, #74877a);
  cursor: pointer;
  font-size: 11px;
}
@media (max-width: 600px) {
  .appearance-panel {
    top: calc(var(--dex-header-height, 68px) + 8px);
    max-height: min(640px, calc(100dvh - var(--dex-header-height, 68px) - 80px));
  }
}
</style>
