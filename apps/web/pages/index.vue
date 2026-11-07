<script setup lang="ts">
const { locale } = useI18n()
useSeoMeta({
  title: () => (locale.value === 'zh-Hans' ? 'PokéCodex · 图鉴首页' : 'PokéCodex · Pokédex home'),
  description: () =>
    locale.value === 'zh-Hans'
      ? '穿过薄雾与树林，探索宝可梦、招式、道具与属性。'
      : 'Explore Pokémon, moves, items and types under the moonlight.',
  ogType: 'website',
})
</script>

<template><NightHome /></template>
