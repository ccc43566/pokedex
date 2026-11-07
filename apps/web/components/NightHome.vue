<script setup lang="ts">
import { nightVisitors, nightVisitorName, nightVisitorStyle } from '~/utils/nightHome'
import '~/assets/css/night-home.css'
import '~/assets/css/night-home-integration.css'

const { locale, t } = useI18n()
const localePath = useLocalePath()
const switchLocalePath = useSwitchLocalePath()
const route = useRoute()
const home = ref<HTMLElement | null>(null)
const ready = ref(false)
onMounted(() => { ready.value = true })
const search = ref(typeof route.query.q === 'string' ? route.query.q : '')
const ambient = ref(true)
const lit = ref<number[]>([])
const lampVisitors = [711, 778, 607, 94, 710]
const selectedGuest = computed(() =>
  nightVisitors.find((row) => row.id === lampVisitors[lit.value.at(-1) ?? -1]),
)
const isChinese = computed(() => locale.value === 'zh-Hans')
const text = (zh: string, en: string) => (isChinese.value ? zh : en)
const navigation = [
  { path: '/pokemon', icon: 'ball', zh: '宝可梦', en: 'Pokémon' },
  { path: '/moves', icon: 'move', zh: '招式', en: 'Moves' },
  { path: '/items', icon: 'bag', zh: '道具', en: 'Items' },
  { path: '/types', icon: 'type', zh: '属性', en: 'Types' },
]
const letters = [...'PokéCodex']
const detailLocation = (id: number) => ({
  path: route.path,
  query: { ...route.query, detail: String(id), form: undefined },
})
function toggleLamp(index: number) {
  lit.value = lit.value.includes(index)
    ? lit.value.filter((value) => value !== index)
    : [...lit.value, index]
}
function submitSearch() {
  const q = search.value.trim()
  void navigateTo(localePath({ path: '/pokemon', query: q ? { q } : {} }))
}
useNightHome(home, ambient)
// Persist once scrolling settles, with immediate flush on navigation/pagehide.
useBrowsePosition(undefined, undefined, { scrollSaveDelay: 150 })
useHead({
  link: [
    {
      rel: 'preload',
      href: '/home/night/Baloo2-variable.ttf',
      as: 'font',
      type: 'font/ttf',
      crossorigin: '',
    },
    { rel: 'preload', href: '/home/night/observatory-night.png', as: 'image' },
  ],
})
</script>

<template>
  <div ref="home" class="night-home">
    <a class="skip-link" href="#home-search">{{ text('跳到搜索', 'Skip to search') }}</a>
    <NightHomeArtwork part="library" />
    <div class="scene scene--framed" aria-hidden="true">
      <div class="scene-art" />
      <div class="scene-shade" />
      <div class="scene-stories" />
      <div class="scene-edge" />
    </div>
    <header id="home-top" class="masthead">
      <div class="masthead-inner">
        <button
          class="brand-trigger"
          type="button"
          :aria-label="text('PokéCodex，重播标志动效', 'PokéCodex, replay logo animation')"
        >
          <span class="night-logo" role="img" aria-label="PokéCodex" data-playing="false">
            <span
              v-for="(word, wi) in [letters.slice(0, 4), letters.slice(4)]"
              :key="wi"
              class="word"
              :class="wi ? 'cdx' : 'pok'"
              aria-hidden="true"
              ><span
                v-for="(letter, index) in word"
                :key="index"
                class="ch"
                :data-c="letter"
                :style="{ '--i': index + (wi ? 4 : 0) }"
                >{{ letter }}</span
              ></span
            >
          </span>
        </button>
        <NightHomeArtwork part="sky" />
      </div>
    </header>
    <nav class="site-nav" :aria-label="text('主导航', 'Main navigation')">
      <div class="nav-inner">
        <a
          class="compact-brand"
          href="#home-top"
          :aria-label="text('PokéCodex，返回顶部', 'PokéCodex, back to top')"
          >Poké<span>Codex</span></a
        >
        <div class="nav-links">
          <NuxtLink
            v-for="item in navigation"
            :key="item.path"
            :to="localePath(item.path)"
            :prefetch="false"
            ><svg aria-hidden="true"><use :href="`#home-i-${item.icon}`" /></svg
            ><span>{{ text(item.zh, item.en) }}</span></NuxtLink
          >
        </div>
      </div>
    </nav>
    <section class="hero-intro" aria-labelledby="home-night-title">
      <div class="hero-inner">
        <div class="search-copy">
          <p class="season-note">
            <span aria-hidden="true">✦</span
            >{{ text('万圣夜，研究所的灯还亮着。', 'The laboratory lights are still on tonight.') }}
          </p>
          <h1 id="home-night-title">
            {{ text('今夜，去认识', 'Meet the Pokémon') }}<br >{{
              text('月光下的宝可梦。', 'under the moonlight.')
            }}
          </h1>
          <p class="hero-description">
            {{
              text(
                '穿过薄雾与树林，从一个名字开始探索。',
                'Through mist and woodland, start exploring with a name.',
              )
            }}
          </p>
          <form class="home-search-form" role="search" @submit.prevent="submitSearch">
            <label class="sr-only" for="home-search">{{
              text('搜索全部宝可梦名称或编号', 'Search all Pokémon by name or number')
            }}</label>
            <div class="search-field">
              <svg aria-hidden="true"><use href="#home-i-search" /></svg
              ><input
                id="home-search"
                v-model="search"
              :disabled="!ready"
                name="q"
                type="search"
                :placeholder="text('搜索名称或编号', 'Name or number')"
                autocomplete="off"
              >
            </div>
          <button type="submit" class="search-button" :disabled="!ready">{{ text('搜索', 'Search') }}</button>
          </form>
        </div>
      </div>
      <img
        class="wandering-ghost"
        :src="nightVisitors.find((row) => row.id === 92)!.sprite"
        alt=""
        aria-hidden="true"
        width="96"
        height="96"
      >
      <img
        class="quiet-ghost"
        :src="nightVisitors.find((row) => row.id === 353)!.sprite"
        alt=""
        aria-hidden="true"
        width="96"
        height="96"
      >
      <NightHomeArtwork part="branches" />
      <div class="ground-mist" aria-hidden="true" />
    </section>
    <section class="catalog" aria-labelledby="home-catalog-title">
      <div class="catalog-inner">
        <div class="catalog-heading">
          <h2 id="home-catalog-title">{{ text('林间的访客', 'Visitors in the woods') }}</h2>
          <div class="catalog-actions">
            <NuxtLink :to="localePath('/pokemon')" class="all-pokemon" :prefetch="false">{{
              text('查看全部图鉴', 'Explore the Pokédex')
            }}</NuxtLink>
          </div>
        </div>
        <div
          class="night-visitors"
          role="list"
          :aria-label="text('万圣夜精选宝可梦', 'Featured Halloween Pokémon')"
        >
          <div
            v-for="pokemon in nightVisitors"
            :key="pokemon.id"
            class="visitor-place"
            role="listitem"
          >
            <NuxtLink
              :to="detailLocation(pokemon.id)"
              :prefetch="false"
              class="visitor"
              :class="{ 'visitor--pumpkin': pokemon.id === 710 || pokemon.id === 711 }"
              :data-id="pokemon.id"
              :aria-label="`${pokemon.displayNumber} ${nightVisitorName(pokemon, locale)}，${text('查看详情', 'View details')}`"
            >
              <span class="visitor-sprite"
                ><span class="visitor-motion"
                  ><img
                    class="visitor-image"
                    :style="nightVisitorStyle(pokemon)"
                    :src="pokemon.sprite"
                    alt=""
                    width="96"
                    height="96"
                    loading="lazy"
                    decoding="async"
                    data-playing="false" ></span
              ></span>
              <span class="visitor-name">{{ nightVisitorName(pokemon, locale) }}</span
              ><span class="visitor-number">#{{ pokemon.displayNumber }}</span>
            </NuxtLink>
          </div>
        </div>
        <section
          class="lantern-yard"
          :aria-label="
            text('点亮南瓜灯，邀请宝可梦', 'Light a pumpkin lantern to invite a Pokémon')
          "
        >
          <div class="lantern-guest-space">
            <NuxtLink
              v-if="selectedGuest"
              class="lantern-guest"
              :to="detailLocation(selectedGuest.id)"
              :prefetch="false"
              ><img :src="selectedGuest.sprite" width="96" height="96" alt="" ><span>{{
                nightVisitorName(selectedGuest, locale)
              }}</span></NuxtLink
            >
          </div>
          <div class="lanterns" role="group" :aria-label="text('南瓜灯', 'Pumpkin lanterns')">
            <button
              v-for="(_, index) in lampVisitors"
              :key="index"
              type="button"
              class="jack"
              :aria-pressed="lit.includes(index)"
              :aria-label="
                text(
                  `${lit.includes(index) ? '熄灭' : '点亮'}第${index + 1}盏南瓜灯`,
                  `${lit.includes(index) ? 'Extinguish' : 'Light'} pumpkin lantern ${index + 1}`,
                )
              "
              @click="toggleLamp(index)"
            >
              <NightHomeArtwork part="lantern" />
            </button>
          </div>
          <p class="lantern-status" role="status">
            {{
              selectedGuest
                ? text(
                    `${selectedGuest.name}来到了灯边。`,
                    `${selectedGuest.englishName} has joined the lanterns.`,
                  )
                : text(
                    '点亮一盏南瓜灯，邀请一位访客。',
                    'Light a pumpkin lantern to invite a visitor.',
                  )
            }}
          </p>
          <div class="lantern-actions">
            <button v-show="lit.length" type="button" class="reset-lamps" @click="lit = []">
              {{ text('熄灯', 'Extinguish all') }}
            </button>
          </div>
        </section>
      </div>
    </section>
    <footer class="page-footer">
      <div class="page-footer-inner">
        <strong>PokéCodex</strong><span>{{ text('图鉴首页', 'Pokédex home') }}</span>
        <div class="home-settings">
          <AppCheckbox id="home-ambient" v-model="ambient" :label="text('环境动效', 'Ambient animation')" />
          <label class="home-language"
            ><span class="sr-only">{{ text('语言', 'Language') }}</span
            ><select
              :value="locale"
              @change="
                navigateTo(
                  switchLocalePath(($event.target as HTMLSelectElement).value as 'zh-Hans' | 'en'),
                )
              "
            >
              <option value="zh-Hans">简体中文</option>
              <option value="en">English</option>
            </select></label
          >
        </div>
        <p class="home-attribution">{{ t('app.attribution') }}</p>
      </div>
    </footer>
  </div>
</template>
