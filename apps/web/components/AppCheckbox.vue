<script setup lang="ts">
defineOptions({ inheritAttrs: false })
defineProps<{
  modelValue?: boolean
  label: string
  disabled?: boolean
  id?: string
  name?: string
}>()
defineEmits<{ 'update:modelValue': [value: boolean] }>()
</script>

<template>
  <label class="ui-check" :class="{ 'ui-check--disabled': disabled }">
    <input
      v-bind="$attrs"
      :id="id"
      :name="name"
      class="ui-check__input"
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <span class="ui-check__box" aria-hidden="true"
      ><svg viewBox="0 0 16 16" fill="none">
        <path
          d="m3.5 8 3 3 6-6"
          pathLength="1"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        /></svg
    ></span>
    <span>{{ label }}</span>
  </label>
</template>

<style scoped>
.ui-check {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: inherit;
  cursor: pointer;
}
.ui-check__input {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1;
  width: 17px;
  height: 17px;
  opacity: 0;
  margin: 0;
  padding: 0;
  border: 0;
}
.ui-check__box {
  display: inline-flex;
  flex: none;
  width: 17px;
  height: 17px;
  border: 1px solid var(--catalog-panel-line, #99ada2);
  border-radius: 5px;
  background: var(--catalog-panel-bg, #fff);
  color: var(--catalog-panel-bg, #fff);
  align-items: center;
  justify-content: center;
}
.ui-check__box svg {
  width: 15px;
  height: 15px;
}
.ui-check__box path {
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  transition: stroke-dashoffset 180ms ease-out;
}
.ui-check__input:checked + .ui-check__box {
  background: var(--ui-primary, #3e6650);
  border-color: var(--ui-primary, #3e6650);
}
.ui-check__input:checked + .ui-check__box path {
  stroke-dashoffset: 0;
}
.ui-check__input:focus-visible + .ui-check__box {
  outline: 2px solid var(--ui-primary, #3e6650);
  outline-offset: 3px;
}
.ui-check--disabled {
  opacity: 0.5;
  cursor: default;
}
@media (prefers-reduced-motion: reduce) {
  .ui-check__box path {
    transition: none;
  }
}
</style>
