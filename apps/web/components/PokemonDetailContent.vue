<script setup lang="ts">
import type { PokemonDetail } from '~/types/api'
import { formatDexNumber } from '~/utils/pokemon'

defineProps<{ pokemon: PokemonDetail; compact?: boolean }>()
const { t } = useI18n()
const localePath = useLocalePath()
</script>

<template>
  <article class="detail-sheet" :class="{ 'detail-sheet--compact': compact }">
    <div class="detail-sheet__hero">
      <div class="detail-sheet__art">
        <NuxtImg
          v-if="pokemon.artworkUrl || pokemon.spriteUrl"
          :src="pokemon.artworkUrl || pokemon.spriteUrl || ''"
          :alt="pokemon.localizedName"
          width="512"
          height="512"
          class="detail-sheet__image"
          loading="eager"
        />
        <span v-else class="text-5xl text-[#667685]">?</span>
      </div>
      <div class="detail-sheet__intro">
        <div class="flex flex-wrap items-center gap-2">
          <span class="detail-sheet__number">{{ formatDexNumber(pokemon.id) }}</span>
          <span v-if="pokemon.isLegendary" class="detail-sheet__marker">{{
            t('pokemon.legendaryShort')
          }}</span>
          <span v-if="pokemon.isMythical" class="detail-sheet__marker">{{
            t('pokemon.mythicalShort')
          }}</span>
        </div>
        <component :is="compact ? 'h2' : 'h1'" class="detail-sheet__name">
          {{ pokemon.localizedName }}
        </component>
        <p class="text-sm text-[#667685]">{{ pokemon.name }}</p>
        <p v-if="pokemon.genus" class="mt-3 text-sm font-semibold text-[#667685]">
          {{ pokemon.genus }}
        </p>
        <div class="mt-4 flex flex-wrap gap-2">
          <TypeBadge v-for="type in pokemon.types" :key="type.id" :type="type" link />
        </div>
        <p v-if="pokemon.description" class="mt-5 leading-7 text-[#344554]">
          {{ pokemon.description }}
        </p>
        <dl class="detail-sheet__metrics">
          <div>
            <dt>{{ t('pokemon.height') }}</dt>
            <dd>{{ pokemon.height ? `${pokemon.height / 10} m` : '—' }}</dd>
          </div>
          <div>
            <dt>{{ t('pokemon.weight') }}</dt>
            <dd>{{ pokemon.weight ? `${pokemon.weight / 10} kg` : '—' }}</dd>
          </div>
          <div>
            <dt>{{ t('pokemon.baseExperience') }}</dt>
            <dd>{{ pokemon.baseExperience ?? '—' }}</dd>
          </div>
        </dl>
      </div>
    </div>

    <div class="detail-sheet__sections">
      <section class="detail-sheet__section">
        <h3>{{ t('pokemon.stats') }}</h3>
        <StatBars :stats="pokemon.stats" />
      </section>
      <section class="detail-sheet__section">
        <h3>{{ t('pokemon.abilities') }}</h3>
        <div class="space-y-4">
          <article
            v-for="ability in pokemon.abilities"
            :key="ability.id"
            class="detail-sheet__ability"
          >
            <div class="flex flex-wrap items-center gap-2">
              <NuxtLink
                :to="localePath(`/abilities/${ability.name}`)"
                class="font-bold hover:text-[#E84A4A]"
              >
                {{ ability.localizedName }}
              </NuxtLink>
              <UBadge v-if="ability.isHidden" color="warning" variant="soft">{{
                t('pokemon.hiddenAbility')
              }}</UBadge>
            </div>
            <p
              v-if="ability.shortEffect || ability.effect"
              class="mt-2 text-sm leading-6 text-[#667685]"
            >
              {{ ability.shortEffect || ability.effect }}
            </p>
          </article>
        </div>
      </section>
    </div>

    <PokemonVersionGallery :pokemon="pokemon" />

    <section v-if="pokemon.evolutionChain.length" class="detail-sheet__section">
      <h3>{{ t('pokemon.evolution') }}</h3>
      <div class="overflow-x-auto pb-4">
        <div class="flex min-w-max justify-center gap-8">
          <EvolutionTree
            v-for="node in pokemon.evolutionChain"
            :key="node.speciesId"
            :node="node"
          />
        </div>
      </div>
    </section>

    <section v-if="pokemon.forms.length" class="detail-sheet__section">
      <h3>{{ t('pokemon.forms') }}</h3>
      <div class="detail-sheet__forms">
        <div v-for="form in pokemon.forms" :key="form.id" class="detail-sheet__form">
          <div class="grid h-28 place-items-center">
            <NuxtImg
              v-if="form.spriteUrl"
              :src="form.spriteUrl"
              :alt="form.name"
              class="max-h-24 object-contain"
            />
          </div>
          <p class="font-bold">{{ form.formName || form.name }}</p>
          <p class="text-xs text-[#667685]">{{ form.name }}</p>
        </div>
      </div>
    </section>
  </article>
</template>

<style scoped>
.detail-sheet {
  display: grid;
  gap: 1.25rem;
  color: #1b2733;
}
.detail-sheet__hero,
.detail-sheet__section {
  border: 1px solid #ccd7de;
  background: #fff;
  border-radius: 1rem;
  overflow: hidden;
}
.detail-sheet__hero {
  display: grid;
  grid-template-columns: minmax(0, 0.85fr) minmax(0, 1.15fr);
}
.detail-sheet__art {
  display: grid;
  min-height: 24rem;
  place-items: center;
  padding: 1.5rem;
  background: #f2f6f8;
}
.detail-sheet__image {
  max-width: 100%;
  max-height: 21rem;
  object-fit: contain;
}
.detail-sheet__intro {
  min-width: 0;
  padding: 2rem;
}
.detail-sheet__number {
  border-left: 3px solid #e84a4a;
  border-radius: 0.25rem;
  background: #e9eff3;
  padding: 0.3rem 0.55rem;
  font-size: 0.8rem;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}
.detail-sheet__marker {
  border: 1px solid #ccd7de;
  border-radius: 0.3rem;
  padding: 0.2rem 0.45rem;
  font-size: 0.75rem;
  font-weight: 700;
}
.detail-sheet__name {
  overflow-wrap: anywhere;
  margin-top: 1rem;
  font-size: clamp(2rem, 3vw, 3rem);
  font-weight: 850;
  line-height: 1.18;
  letter-spacing: -0.035em;
}
.detail-sheet__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 1.5rem;
}
.detail-sheet__metrics > div {
  min-width: 0;
  border-top: 1px solid #ccd7de;
  padding-top: 0.6rem;
}
.detail-sheet__metrics dt {
  font-size: 0.72rem;
  color: #667685;
}
.detail-sheet__metrics dd {
  margin-top: 0.2rem;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}
.detail-sheet__sections {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1.25rem;
}
.detail-sheet__section {
  min-width: 0;
  padding: 1.5rem;
}
.detail-sheet__section h3 {
  margin-bottom: 1.2rem;
  font-size: 1.35rem;
  font-weight: 800;
}
.detail-sheet__ability {
  border-top: 1px solid #e4ecf0;
  padding-top: 0.8rem;
}
.detail-sheet__forms {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.7rem;
}
.detail-sheet__form {
  min-width: 0;
  border: 1px solid #e4ecf0;
  border-radius: 0.65rem;
  padding: 0.75rem;
}
.detail-sheet--compact {
  gap: 0.75rem;
}
.detail-sheet--compact .detail-sheet__hero,
.detail-sheet--compact .detail-sheet__sections {
  display: block;
}
.detail-sheet--compact .detail-sheet__art {
  min-height: 14rem;
  height: 14rem;
}
.detail-sheet--compact .detail-sheet__image {
  max-height: 13rem;
}
.detail-sheet--compact .detail-sheet__intro {
  padding: 1.25rem;
}
.detail-sheet--compact .detail-sheet__name {
  font-size: 2rem;
}
.detail-sheet--compact .detail-sheet__section {
  margin-top: 0.75rem;
  padding: 1.25rem;
}
.detail-sheet--compact .detail-sheet__forms {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
@media (max-width: 767px) {
  .detail-sheet__hero,
  .detail-sheet__sections {
    display: block;
  }
  .detail-sheet__art {
    min-height: 17rem;
    height: 17rem;
  }
  .detail-sheet__image {
    max-height: 16rem;
  }
  .detail-sheet__intro,
  .detail-sheet__section {
    padding: 1.25rem;
  }
  .detail-sheet__sections .detail-sheet__section + .detail-sheet__section {
    margin-top: 1.25rem;
  }
  .detail-sheet__forms {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
