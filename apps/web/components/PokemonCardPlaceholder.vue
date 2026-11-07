<script setup lang="ts">
import type { PokemonListItem } from '~/types/api'
defineProps<{ pokemon: PokemonListItem }>()
</script>

<template>
  <!-- Real labels reserve the same wrapped line heights as the final card. -->
  <div class="pokemon-card-placeholder" aria-hidden="true">
    <div class="pokemon-card__top" />
    <div class="pokemon-card__art" />
    <div class="pokemon-card__details">
      <h2 class="pokemon-card__name">
        <span>{{ pokemon.localizedName }}</span
        ><span v-if="pokemon.variantLabel" class="pokemon-card__form-label"
          >（{{ pokemon.variantLabel }}）</span
        >
      </h2>
      <div class="pokemon-card__types" style="height: 30px" />
    </div>
  </div>
</template>

<style scoped>
.pokemon-card-placeholder {
  visibility: hidden;
  pointer-events: none;
}
</style>
