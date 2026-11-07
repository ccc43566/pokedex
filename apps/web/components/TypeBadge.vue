<script setup lang="ts">
import { NuxtLink } from '#components'
import { isVisibleType, typeColors, type PresentedType } from '~/utils/typePresentation'
const props = defineProps<{
  type: PresentedType
  label?: string
  link?: boolean
  compact?: boolean
  size?: 'compact' | 'standard' | 'card'
}>()
const localePath = useLocalePath()
const colors = computed(() => typeColors(props.type.name))
const variant = computed(() => props.size || (props.compact ? 'compact' : 'standard'))
</script>

<template>
  <component
    :is="link ? NuxtLink : 'span'"
    v-if="isVisibleType(type)"
    :to="link ? localePath(`/types/${type.name}`) : undefined"
    class="type-bar"
    :class="`type-bar--${variant}`"
    :data-type="type.name"
    :data-size="variant"
    :style="{ '--type-icon-bg': colors.icon, '--type-label-bg': colors.label }"
  >
    <span class="type-bar__icon" aria-hidden="true"
      ><img
        :src="`/type-icons/${type.name === 'stellar' ? 'stellar.png' : `${type.name}.svg`}`"
        alt=""
        width="23"
        height="23"
        decoding="async"
    ></span>
    <span class="type-bar__name">{{ label ?? type.localizedName }}</span>
  </component>
</template>

<style scoped>
.type-bar {
  --bar-height: 32px;
  --bar-left: 38px;
  --bar-font: 13px;
  --bar-icon: 23px;
  display: inline-flex;
  align-items: stretch;
  flex: none;
  width: 104px;
  min-width: 104px;
  height: var(--bar-height);
  border-radius: 6px;
  overflow: hidden;
  isolation: isolate;
  background: var(--type-label-bg);
  color: #fff;
  vertical-align: middle;
  text-decoration: none;
  line-height: 1;
  box-sizing: border-box;
}
.type-bar__icon {
  position: relative;
  display: grid;
  place-items: center;
  width: var(--bar-left);
  flex: none;
}
.type-bar__icon::before {
  content: '';
  position: absolute;
  inset: 0 -6px 0 0;
  background: var(--type-icon-bg);
  clip-path: polygon(0 0, 100% 0, calc(100% - 9px) 100%, 0 100%);
  z-index: -1;
}
.type-bar__icon img {
  width: var(--bar-icon);
  height: var(--bar-icon);
  object-fit: contain;
  margin-left: -2px;
}
.type-bar__name {
  display: flex;
  flex: 1;
  min-width: 0;
  align-items: center;
  justify-content: center;
  padding: 0 6px;
  font-size: var(--bar-font);
  font-weight: 750;
  color: #fff;
  text-align: center;
  line-height: 1.02;
  overflow-wrap: anywhere;
}
.type-bar--compact {
  --bar-height: 24px;
  --bar-left: 27px;
  --bar-font: 11px;
  --bar-icon: 18px;
  width: 84px;
  min-width: 84px;
  border-radius: 5px;
}
.type-bar--card {
  --bar-height: 30px;
  --bar-left: 23px;
  --bar-font: 13px;
  --bar-icon: 22px;
  width: var(--card-type-width, 100%);
  min-width: 0;
  flex: 0 0 var(--card-type-width, 100%);
  border-radius: 5px;
}
.type-bar--card .type-bar__name {
  padding: 0;
}
.type-bar--card .type-bar__icon img {
  margin-left: 0;
}
a.type-bar:focus-visible {
  outline: 3px solid #e84a4a;
  outline-offset: 3px;
}
</style>
