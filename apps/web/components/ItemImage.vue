<script setup lang="ts">
const props = defineProps<{ itemId: number; src?: string | null; name: string }>()
const { tr } = useReferenceText()
const failed = ref(false)
const imageElement = ref<HTMLImageElement | null>(null)
// An SSR image can fail before Vue attaches its error handler during hydration.
onMounted(() => {
  if (props.src && imageElement.value?.complete && imageElement.value.naturalWidth === 0) {
    failed.value = true
  }
})
watch(
  () => [props.itemId, props.src],
  () => {
    failed.value = false
  },
)
function onError(event: Event) {
  const image = event.target as HTMLImageElement
  if (image.dataset.itemId === String(props.itemId) && image.getAttribute('src') === props.src) {
    failed.value = true
  }
}
</script>

<template>
  <span class="item-image">
    <img
      v-if="src && !failed"
      ref="imageElement"
      :key="`${itemId}:${src}`"
      :src="src"
      :alt="name"
      :data-item-id="itemId"
      width="64"
      height="64"
      loading="lazy"
      decoding="async"
      @error="onError"
    >
    <span
      v-else
      class="item-image__missing"
      role="img"
      :aria-label="`${name} · ${tr('暂无图片', 'No image')}`"
    >
      {{ tr('暂无图片', 'No image') }}
    </span>
  </span>
</template>

<style scoped>
.item-image {
  display: inline-grid;
  place-items: center;
  width: 64px;
  height: 64px;
  flex-shrink: 0;
}
.item-image img {
  width: 64px;
  height: 64px;
  object-fit: contain;
  image-rendering: pixelated;
}
.item-image__missing {
  font-size: 0.7rem;
  line-height: 1.4;
  color: #667685;
  text-align: center;
}
</style>
