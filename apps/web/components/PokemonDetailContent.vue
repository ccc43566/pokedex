<script setup lang="ts">
import type { PokemonDetail, PokemonFormOption } from '~/types/api'
import { currentFormOption, formatDexNumber } from '~/utils/pokemon'
import { isVisibleType } from '~/utils/typePresentation'
import { genderRatio } from '~/utils/detailFacts'

const props = defineProps<{ pokemon: PokemonDetail; compact?: boolean }>()
const { t, locale } = useI18n()
const localePath = useLocalePath()
const route = useRoute()
const navigation = usePokemonNavigation(() => Boolean(props.compact))
const interactive = ref(false)
onMounted(() => {
  interactive.value = true
})
const options = computed(() => props.pokemon.formOptions || [])
const selection = computed(() => currentFormOption(props.pokemon, route.query.form))
const title = computed(
  () => selection.value?.label || props.pokemon.displayName || props.pokemon.localizedName,
)
const image = computed(
  () =>
    selection.value?.artworkUrl ||
    selection.value?.spriteUrl ||
    (selection.value?.isDefault !== false
      ? props.pokemon.artworkUrl || props.pokemon.spriteUrl
      : null),
)
const types = computed(() =>
  (selection.value?.types.length ? selection.value.types : props.pokemon.types).filter(
    isVisibleType,
  ),
)

async function selectForm(key: string) {
  const option: PokemonFormOption | undefined = options.value.find((item) => item.key === key)
  if (!option) return
  await navigation.select({ pokemonId: option.pokemonId, formKey: option.key })
}
</script>

<template>
  <article class="detail-sheet" :class="{ 'detail-sheet--compact': compact }">
    <section v-if="selection" class="detail-sheet__section detail-form-picker">
      <label class="font-bold" :for="compact ? 'drawer-form-choice' : 'page-form-choice'">{{
        t('pokemon.forms')
      }}</label>
      <select
        :id="compact ? 'drawer-form-choice' : 'page-form-choice'"
        class="detail-form-select"
        :value="selection.key"
        :disabled="!interactive || options.length < 2"
        @change="selectForm(($event.target as HTMLSelectElement).value)"
      >
        <option v-for="item in options" :key="item.key" :value="item.key">
          {{ item.displayNumber }} {{ item.label }}
        </option>
      </select>
    </section>
    <div class="detail-sheet__hero">
      <div class="detail-sheet__art">
        <NuxtImg
          v-if="image"
          :src="image"
          :alt="title"
          width="512"
          height="512"
          class="detail-sheet__image"
          loading="eager"
        />
        <span v-else class="text-5xl text-[#667685]">?</span>
      </div>
      <div class="detail-sheet__intro">
        <div class="flex flex-wrap items-center gap-2">
          <span class="detail-sheet__number">{{
            formatDexNumber(pokemon.displayNumber || pokemon.id)
          }}</span>
          <span v-if="pokemon.isLegendary" class="detail-sheet__marker">{{
            t('pokemon.legendaryShort')
          }}</span>
          <span v-if="pokemon.isMythical" class="detail-sheet__marker">{{
            t('pokemon.mythicalShort')
          }}</span>
        </div>
        <component :is="compact ? 'h2' : 'h1'" class="detail-sheet__name">
          {{ title }}
        </component>
        <p class="text-sm text-[#667685]">{{ pokemon.name }}</p>
        <p v-if="pokemon.genus" class="mt-3 text-sm font-semibold text-[#667685]">
          {{ pokemon.genus }}
        </p>
        <div class="mt-4 flex flex-wrap gap-2">
          <TypeBadge v-for="type in types" :key="type.id" :type="type" link />
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
            <dt>{{ t('pokemon.eggGroups') }}</dt>
            <dd data-egg-groups>
              {{ pokemon.eggGroups?.map((group) => group.localizedName).join(' / ') || '—' }}
            </dd>
          </div>
          <div class="detail-sheet__gender">
            <dt>{{ t('pokemon.genderRatio') }}</dt>
            <dd data-gender-ratio>{{ genderRatio(pokemon.genderRate, locale) }}</dd>
          </div>
        </dl>
      </div>
    </div>

    <div class="detail-sheet__sections">
      <section class="detail-sheet__section detail-sheet__stats">
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

    <section class="detail-sheet__section" data-stat-history>
      <h3>{{ t('pokemon.statHistory') }}</h3>
      <ul v-if="pokemon.statChanges?.length" class="space-y-3">
        <li
          v-for="change in pokemon.statChanges"
          :key="`${change.generationId}:${change.previousName}:${change.name}`"
          class="flex flex-wrap gap-x-3 gap-y-1 text-sm"
        >
          <strong>{{ t('pokemon.changeGeneration', { generation: change.generationId }) }}</strong>
          <span>
            {{
              change.isSplit
                ? `${change.previousLocalizedName} → ${change.localizedName}`
                : change.localizedName
            }}
          </span>
          <span class="font-bold tabular-nums">{{ change.oldValue }} → {{ change.newValue }}</span>
          <span v-if="change.isSplit" class="text-[#667685]">{{ t('pokemon.specialSplit') }}</span>
        </li>
      </ul>
      <p v-else class="text-sm text-[#667685]">
        {{
          t(pokemon.statHistoryAvailable ? 'pokemon.noStatChanges' : 'pokemon.statHistoryMissing')
        }}
      </p>
      <p v-if="pokemon.statChanges?.length" class="mt-3 text-xs text-[#667685]">
        {{ t('pokemon.statHistoryNote') }}
      </p>
    </section>

    <PokemonVersionGallery v-if="selection" :pokemon="pokemon" :selection="selection" />

    <section v-if="pokemon.evolutionGraph?.nodes.length" class="detail-sheet__section">
      <h3>{{ t('pokemon.evolution') }}</h3>
      <EvolutionTree :graph="pokemon.evolutionGraph" :compact="compact" />
    </section>

    <section class="detail-sheet__section" data-species-forms>
      <h3>{{ locale === 'zh-Hans' ? '此宝可梦形态' : 'Forms of this Pokémon' }}</h3>
      <div class="detail-sheet__forms">
        <button
          v-for="item in options"
          :key="item.key"
          type="button"
          class="detail-sheet__form"
          :class="{ 'detail-sheet__form--current': item.key === selection?.key }"
          :data-form-key="item.key"
          :aria-pressed="item.key === selection?.key"
          :disabled="!interactive"
          @click="selectForm(item.key)"
        >
          <NuxtImg
            v-if="item.artworkUrl || item.spriteUrl"
            :src="(item.artworkUrl || item.spriteUrl)!"
            :alt="item.label"
            width="96"
            height="96"
            loading="lazy"
          />
          <span v-else class="detail-sheet__form-missing" aria-hidden="true">?</span>
          <span class="text-xs text-[#667685]">{{ formatDexNumber(item.displayNumber) }}</span>
          <strong>{{ item.label }}</strong>
          <span v-if="item.key === selection?.key" class="text-xs text-[#b42a2a]">{{
            t('pokemon.selected')
          }}</span>
        </button>
      </div>
    </section>
  </article>
</template>

<style scoped>
.detail-form-select {
  display: block;
  width: 100%;
  min-width: 0;
  margin-top: 0.5rem;
  padding: 0.6rem;
  border: 1px solid var(--catalog-panel-line,#ccd7de);
  border-radius: 0.5rem;
  background: var(--catalog-panel-bg,#fff);
}
.detail-form-select:focus-visible {
  outline: 3px solid #e84a4a;
  outline-offset: 2px;
}
.detail-sheet {
  display: grid;
  gap: 1.25rem;
  color: var(--catalog-panel-text,#1b2733);
}
.detail-sheet__hero,
.detail-sheet__section {
  border: 1px solid var(--catalog-panel-line,#ccd7de);
  background: var(--catalog-panel-bg,#fff);
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
  background: var(--catalog-panel-inset,#f2f6f8);
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
  background: var(--catalog-panel-inset,#e9eff3);
  padding: 0.3rem 0.55rem;
  font-size: 0.8rem;
  font-weight: 750;
  font-variant-numeric: tabular-nums;
}
.detail-sheet__marker {
  border: 1px solid var(--catalog-panel-line,#ccd7de);
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 1.5rem;
}
.detail-sheet__metrics > div {
  min-width: 0;
  border-top: 1px solid var(--catalog-panel-line,#ccd7de);
  padding-top: 0.6rem;
}
.detail-sheet__metrics dt {
  font-size: 0.72rem;
  color: var(--catalog-panel-muted,#667685);
}
.detail-sheet__metrics dd {
  overflow-wrap: anywhere;
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
.detail-sheet__stats h3 {
  text-align: center;
}
.detail-sheet__ability {
  border-top: 1px solid var(--catalog-panel-line,#e4ecf0);
  padding-top: 0.8rem;
}
.detail-sheet__forms {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.7rem;
}
.detail-sheet__form {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  text-align: center;
  overflow-wrap: anywhere;
  min-width: 0;
  border: 1px solid var(--catalog-panel-line,#e4ecf0);
  border-radius: 0.65rem;
  padding: 0.75rem;
  cursor: pointer;
}
.detail-sheet__form img,
.detail-sheet__form-missing {
  width: 6rem;
  height: 6rem;
  object-fit: contain;
}
.detail-sheet__form-missing {
  display: grid;
  place-items: center;
  font-size: 2rem;
  color: var(--catalog-panel-muted,#667685);
}
.detail-sheet__form--current {
  border: 2px solid #e84a4a;
  background: var(--catalog-selected-bg,#fff6f5);
}
.detail-sheet__form:focus-visible {
  outline: 3px solid #e84a4a;
  outline-offset: 2px;
}
.detail-sheet__form strong {
  font-size: 0.85rem;
}
.detail-sheet__form:hover {
  border-color: #e84a4a;
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
