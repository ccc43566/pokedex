<script setup lang="ts">
import type { PokemonDetail, PokemonVersionMedia, VersionSpriteOut } from '~/types/api'

const props = defineProps<{ pokemon: PokemonDetail }>()
const { locale } = useI18n()
const zh = computed(() => locale.value === 'zh-Hans')
const data = shallowRef<PokemonVersionMedia | null>(null)
const loading = ref(false)
const error = ref(false)
const owner = ref('')
const generation = ref('all')
const game = ref('all')
const kind = ref('front_default')
const showMissing = ref(false)
const generationOrder = ['generation-i', 'generation-ii', 'generation-iii', 'generation-iv',
  'generation-v', 'generation-vi', 'generation-vii', 'generation-viii', 'generation-ix']
let requestId = 0
const gameNames: Record<string, string> = {
  'red-blue': '红／蓝', 'red-green-japan': '红／绿（日版）', yellow: '黄',
  gold: '金', silver: '银', crystal: '水晶',
  'ruby-sapphire': '红宝石／蓝宝石', emerald: '绿宝石', 'firered-leafgreen': '火红／叶绿',
  'diamond-pearl': '钻石／珍珠', platinum: '白金', 'heartgold-soulsilver': '心金／魂银',
  'black-white': '黑／白', 'x-y': 'X／Y',
  'omega-ruby-alpha-sapphire': '欧米伽红宝石／阿尔法蓝宝石',
  'ultra-sun-ultra-moon': '究极之日／究极之月',
  'lets-go-pikachu-lets-go-eevee': "Let's Go 皮卡丘／伊布",
  'sword-shield': '剑／盾', 'brilliant-diamond-shining-pearl': '晶灿钻石／明亮珍珠',
  'legends-arceus': '传说 阿尔宙斯', 'scarlet-violet': '朱／紫',
  'legends-za': '传说 Z-A', champions: '冠军', icons: '世代图标（无指定游戏）',
}
const kindNames: Record<string, string> = {
  front_default: '正面', front_shiny: '闪光正面', back_default: '背面', back_shiny: '闪光背面',
  front_female: '雌性正面', front_shiny_female: '闪光雌性正面',
  back_female: '雌性背面', back_shiny_female: '闪光雌性背面',
  front_gray: '灰度正面', back_gray: '灰度背面',
  front_transparent: '透明正面', back_transparent: '透明背面',
}
const ownerKey = (row: { ownerType: string; ownerId: number }) => `${row.ownerType}:${row.ownerId}`
function ownerLabel(item: { ownerType: string; name: string }): string {
  if (item.ownerType === 'pokemon') return item.name
  const sameName = item.name === props.pokemon.name
  return `${item.name} ${zh.value ? (sameName ? '（默认形态）' : '（形态）') : (sameName ? '(default form)' : '(form)')}`
}
const ownerRows = computed(() => data.value?.sprites.filter((row) => ownerKey(row) === owner.value) || [])
const generations = computed(() => [...new Set(ownerRows.value.map((row) => row.generation))]
  .sort((a, b) => generationOrder.indexOf(a) - generationOrder.indexOf(b)))
const games = computed(() => [...new Set(ownerRows.value
  .filter((row) => generation.value === 'all' || row.generation === generation.value)
  .map((row) => row.game))].sort())
const kinds = computed(() => [...new Set(ownerRows.value
  .filter((row) => (generation.value === 'all' || row.generation === generation.value)
    && (game.value === 'all' || row.game === game.value))
  .map((row) => row.kind))].sort())
const stats = computed(() => ({
  available: ownerRows.value.filter((row) => row.status === 'downloaded').length,
  missing: ownerRows.value.filter((row) => row.status === 'null').length,
  animated: ownerRows.value.filter((row) => row.status === 'downloaded' && (row.frameCount || 0) > 1).length,
}))
const visible = computed(() => ownerRows.value.filter((row) =>
  (generation.value === 'all' || row.generation === generation.value)
  && (game.value === 'all' || row.game === game.value)
  && (kind.value === 'all' || row.kind === kind.value)
  && (kind.value !== 'all' || showMissing.value || row.status !== 'null')))
const groups = computed(() => {
  const values = new Map<string, { generation: string; rows: VersionSpriteOut[] }>()
  for (const row of visible.value) {
    if (!values.has(row.generation)) values.set(row.generation, { generation: row.generation, rows: [] })
    values.get(row.generation)!.rows.push(row)
  }
  return [...values.values()]
    .sort((a, b) => generationOrder.indexOf(a.generation) - generationOrder.indexOf(b.generation))
    .map((group) => ({ ...group, rows: group.rows.sort((a, b) => a.game.localeCompare(b.game) || a.kind.localeCompare(b.kind)) }))
})
const spriteLookup = computed(() => new Map(ownerRows.value.map((row) =>
  [`${row.generation}/${row.game}/${row.kind}`, row])))

function fallback(row: VersionSpriteOut): VersionSpriteOut | undefined {
  if (row.status !== 'null' || !row.kind.includes('female')) return undefined
  const fallbackKind = row.kind.replace('_shiny_female', '_shiny').replace('_female', '_default')
  const match = spriteLookup.value.get(`${row.generation}/${row.game}/${fallbackKind}`)
  return match?.status === 'downloaded' ? match : undefined
}

function kindLabel(value: string): string {
  const [prefix, ...rest] = value.split('/')
  if (!rest.length) return kindNames[value] || value.replaceAll('_', ' ')
  const label = kindNames[rest.join('/')] || rest.join('/').replaceAll('_', ' ')
  return `${prefix === 'animated' ? (zh.value ? '动画' : 'Animated') : (zh.value ? '图标' : 'Icon')} · ${label}`
}

function gameLabel(value: string): string {
  return zh.value ? (gameNames[value] || value) : value.replaceAll('-', ' ')
}

function generationLabel(value: string): string {
  const number = generationOrder.indexOf(value) + 1
  return zh.value ? `第 ${number} 世代` : `Generation ${number}`
}

watch(() => props.pokemon.id, async (id) => {
  if (!import.meta.client) return
  const currentRequest = ++requestId
  loading.value = true
  error.value = false
  data.value = null
  try {
    const liveUrl = `/api/v1/pokemon/${id}/version-sprites`
    let nextData: PokemonVersionMedia
    try {
      nextData = await $fetch<PokemonVersionMedia>(liveUrl)
    } catch (liveError) {
      if (!import.meta.dev) throw liveError
      nextData = await $fetch<PokemonVersionMedia>(`/api/version-media/${id}`)
    }
    if (currentRequest !== requestId) return
    data.value = nextData
    owner.value = `pokemon:${id}`
    generation.value = 'all'
    game.value = 'all'
    kind.value = 'front_default'
  } catch {
    if (currentRequest === requestId) error.value = true
  } finally {
    if (currentRequest === requestId) loading.value = false
  }
}, { immediate: true })

watch(owner, () => { generation.value = 'all'; game.value = 'all'; kind.value = 'front_default' })
watch(generation, () => { game.value = 'all' })
watch([generation, game], () => { if (kind.value !== 'all' && !kinds.value.includes(kind.value)) kind.value = 'all' })
</script>

<template>
  <section class="version-gallery" aria-labelledby="version-gallery-title">
    <div class="version-gallery__heading">
      <div>
        <h3 id="version-gallery-title">{{ zh ? '历代游戏图片' : 'Images through the games' }}</h3>
        <p>{{ zh ? '同一只宝可梦在不同游戏中的实际图片；GIF 保持动画。' : 'Original game images for this Pokémon, including animated GIFs.' }}</p>
      </div>
      <span v-if="data" class="version-gallery__count">{{ stats.available }} {{ zh ? '张图片' : 'images' }}</span>
    </div>
    <p v-if="loading" class="version-gallery__message">{{ zh ? '正在读取历代图片…' : 'Loading historical images…' }}</p>
    <p v-else-if="error" class="version-gallery__message">{{ zh ? '图片清单暂不可用。采集完成并导出预览后即可查看。' : 'Image catalog is unavailable. Try again after the preview export finishes.' }}</p>
    <template v-else-if="data">
      <div class="version-gallery__controls">
        <label>{{ zh ? '宝可梦／形态' : 'Pokémon / form' }}
          <select v-model="owner"><option v-for="item in data.owners" :key="ownerKey(item)" :value="ownerKey(item)">{{ ownerLabel(item) }}</option></select>
        </label>
        <label>{{ zh ? '世代' : 'Generation' }}
          <select v-model="generation"><option value="all">{{ zh ? '全部世代' : 'All generations' }}</option><option v-for="item in generations" :key="item" :value="item">{{ generationLabel(item) }}</option></select>
        </label>
        <label>{{ zh ? '游戏' : 'Game' }}
          <select v-model="game"><option value="all">{{ zh ? '全部游戏' : 'All games' }}</option><option v-for="item in games" :key="item" :value="item">{{ gameLabel(item) }}</option></select>
        </label>
        <label>{{ zh ? '图片类型' : 'Image type' }}
          <select v-model="kind"><option value="all">{{ zh ? '全部类型' : 'All types' }}</option><option v-for="item in kinds" :key="item" :value="item">{{ kindLabel(item) }}</option></select>
        </label>
      </div>
      <div class="version-gallery__meta">
        <span>{{ stats.missing }} {{ zh ? '个源字段为空' : 'source fields are null' }}</span>
        <span v-if="stats.animated">{{ stats.animated }} {{ zh ? '个动画关联' : 'animated entries' }}</span>
        <label v-if="kind === 'all'"><input v-model="showMissing" type="checkbox" />{{ zh ? '显示空值' : 'Show null fields' }}</label>
      </div>
      <p v-if="!groups.length" class="version-gallery__message">{{ zh ? '此筛选条件下没有图片记录。' : 'No image records match these filters.' }}</p>
      <div v-for="group in groups" :key="group.generation" class="version-gallery__group">
        <h4><span>{{ generationLabel(group.generation) }}</span><strong>{{ group.rows.length }} {{ zh ? '项' : 'entries' }}</strong></h4>
        <div class="version-gallery__grid">
          <article v-for="row in group.rows" :key="`${row.ownerType}/${row.ownerId}/${row.game}/${row.kind}`" class="version-gallery__item">
            <a v-if="row.url || fallback(row)?.url" class="version-gallery__stage" :href="row.url || fallback(row)?.url || '#'" target="_blank" rel="noopener">
              <img :src="row.url || fallback(row)?.url || ''" :alt="`${gameLabel(row.game)} ${kindLabel(row.kind)}`" :class="{ 'version-gallery__artwork': Math.max(row.width || fallback(row)?.width || 0, row.height || fallback(row)?.height || 0) > 256 }" loading="lazy" />
            </a>
            <div v-else class="version-gallery__stage version-gallery__stage--empty">{{ row.status === 'null' ? (zh ? '未提供' : 'Not provided') : row.status === 'pending' ? (zh ? '采集中' : 'Collecting') : (zh ? '待重试' : 'Retry pending') }}</div>
            <div class="version-gallery__item-info">
              <span class="version-gallery__game">{{ gameLabel(row.game) }}</span>
              <strong>{{ kindLabel(row.kind) }}</strong>
              <span v-if="fallback(row)" class="version-gallery__note">{{ zh ? '未提供独立雌性图 · 显示本游戏默认图' : 'No separate female image · game default shown' }}</span>
              <span v-else-if="row.status === 'null'" class="version-gallery__note">{{ zh ? '源字段为空' : 'Source field is null' }}</span>
              <span v-else-if="row.status === 'download_failed' || row.status === 'corrupt'" class="version-gallery__note">{{ row.status === 'corrupt' ? (zh ? '源文件损坏' : 'Corrupt source') : (zh ? '下载失败' : 'Download failed') }}</span>
              <span v-else-if="row.status === 'downloaded'" class="version-gallery__detail">{{ row.format?.toUpperCase() }}{{ (row.frameCount || 0) > 1 ? (zh ? ' · 动画' : ' · Animated') : '' }} · {{ row.byteSize ? `${(row.byteSize / 1024).toFixed(1)} KiB` : '' }}</span>
            </div>
          </article>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.version-gallery { min-width:0; padding:1.5rem; border:1px solid #ccd7de; border-radius:1rem; background:#fff; }
.version-gallery__heading { display:flex; align-items:start; justify-content:space-between; gap:1rem; }
.version-gallery__heading h3 { margin:0; font-size:1.35rem; font-weight:800; }
.version-gallery__heading p { margin:.3rem 0 0; color:#667685; font-size:.85rem; line-height:1.5; }
.version-gallery__count { flex:none; padding:.28rem .55rem; border-left:3px solid #e84a4a; background:#f2f6f8; font-size:.76rem; font-weight:750; }
.version-gallery__controls { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.55rem; margin-top:1.2rem; }
.version-gallery__controls label { display:grid; min-width:0; gap:.3rem; color:#667685; font-size:.72rem; font-weight:700; }
.version-gallery__controls select { min-width:0; width:100%; height:2.4rem; padding:.35rem .5rem; border:1px solid #ccd7de; border-radius:.55rem; background:#fff; color:#1b2733; font-size:.8rem; }
.version-gallery__controls select:focus-visible,.version-gallery__meta input:focus-visible,.version-gallery__stage:focus-visible { outline:3px solid #e84a4a; outline-offset:2px; }
.version-gallery__meta { display:flex; flex-wrap:wrap; gap:.55rem 1rem; align-items:center; margin:.85rem 0 1.1rem; color:#667685; font-size:.75rem; }
.version-gallery__meta label { display:inline-flex; align-items:center; gap:.35rem; cursor:pointer; }
.version-gallery__message { padding:1rem 0; color:#667685; font-size:.85rem; }
.version-gallery__group { margin-top:1.2rem; }
.version-gallery__group h4 { display:flex; align-items:baseline; gap:.6rem; margin:0 0 .55rem; border-bottom:1px solid #ccd7de; padding-bottom:.45rem; }
.version-gallery__group h4 span { color:#e84a4a; font-size:.76rem; font-weight:800; white-space:nowrap; }
.version-gallery__group h4 strong { color:#667685; font-size:.72rem; font-weight:650; }
.version-gallery__grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.5rem; }
.version-gallery__item { min-width:0; border:1px solid #dce5eb; border-radius:.7rem; overflow:hidden; }
.version-gallery__stage { display:grid; place-items:center; height:114px; padding:.4rem; background:repeating-conic-gradient(#f2f6f8 0% 25%,#fff 0% 50%) 50% / 18px 18px; color:#667685; font-size:.75rem; text-align:center; }
.version-gallery__stage:hover { outline:2px solid #e84a4a; outline-offset:-2px; }
.version-gallery__stage img { width:96px; height:96px; max-width:100%; max-height:100%; image-rendering:pixelated; object-fit:contain; }
.version-gallery__stage .version-gallery__artwork { image-rendering:auto; }
.version-gallery__stage--empty { background:#f2f6f8; }
.version-gallery__item-info { display:grid; gap:.2rem; padding:.45rem .55rem .55rem; }
.version-gallery__game { color:#1b2733; font-size:.76rem; font-weight:800; }
.version-gallery__item-info strong { overflow-wrap:anywhere; font-size:.74rem; }
.version-gallery__detail,.version-gallery__note { color:#667685; font-size:.66rem; line-height:1.4; }
.version-gallery__note { color:#9a4e1e; }
@media (max-width:1199px) { .version-gallery__controls { grid-template-columns:repeat(2,minmax(0,1fr)); } .version-gallery__grid { grid-template-columns:repeat(2,minmax(0,1fr)); } }
@media (max-width:620px) { .version-gallery { padding:1rem; } .version-gallery__heading { display:block; } .version-gallery__count { display:inline-block; margin-top:.6rem; } }
</style>
