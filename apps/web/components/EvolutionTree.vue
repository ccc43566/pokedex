<script setup lang="ts">
import type { EvolutionGraph } from '~/types/api'
import { formatDexNumber } from '~/utils/pokemon'

const props = defineProps<{ graph: EvolutionGraph; compact?: boolean }>()
const { locale } = useI18n()
const zh = computed(() => locale.value === 'zh-Hans')
const visibleWarnings = computed(() => props.graph.warnings.filter(warning =>
  warning !== '本地进化条件未明确关联当前形态；未套用普通形态的关系。形态变化不等于进化。',
))
const navigation = usePokemonNavigation(() => Boolean(props.compact))
const plot = ref<HTMLElement | null>(null)
const curves = ref<{ key: string; path: string; x: number; y: number; number: number }[]>([])
const canvas = ref({ width: 1, height: 1 })
const markerId = `evolution-arrow-${useId().replace(/[^a-zA-Z0-9-]/g, '')}`
const layers = computed(() => {
  const depths = new Map(props.graph.nodes.map((node) => [node.key, 0]))
  // Longest path in the acyclic evolution graph. Bounded to protect malformed input.
  for (let pass = 0; pass < props.graph.nodes.length; pass++) {
    let changed = false
    for (const edge of props.graph.edges) {
      const next = (depths.get(edge.source) || 0) + 1
      if (next > (depths.get(edge.target) || 0)) {
        depths.set(edge.target, next)
        changed = true
      }
    }
    if (!changed) break
  }
  const values = [...new Set(depths.values())].sort((a, b) => a - b)
  return values.map((depth) => props.graph.nodes.filter((node) => depths.get(node.key) === depth))
})
const methods = computed(() =>
  props.graph.edges.map((edge, index) => ({
    ...edge,
    methodExplanations: edge.methodExplanations || [],
    number: index + 1,
    sourceNode: props.graph.nodes.find((node) => node.key === edge.source),
    targetNode: props.graph.nodes.find((node) => node.key === edge.target),
  })),
)

function draw() {
  const element = plot.value
  if (!element) return
  const bounds = element.getBoundingClientRect()
  const boxes = new Map(
    [...element.querySelectorAll<HTMLElement>('[data-evolution-node]')].map((node) => [
      node.dataset.evolutionNode!,
      node.getBoundingClientRect(),
    ]),
  )
  canvas.value = { width: bounds.width, height: bounds.height }
  const horizontal = bounds.width >= 640
  curves.value = props.graph.edges.flatMap((edge, index) => {
    const source = boxes.get(edge.source)
    const target = boxes.get(edge.target)
    if (!source || !target) return []
    const incoming = props.graph.edges.filter((e) => e.target === edge.target)
    const outgoing = props.graph.edges.filter((e) => e.source === edge.source)
    const targetPort = (incoming.findIndex((e) => e.key === edge.key) + 1) / (incoming.length + 1)
    const sourcePort = (outgoing.findIndex((e) => e.key === edge.key) + 1) / (outgoing.length + 1)
    if (horizontal) {
      const sx = source.right - bounds.left,
        sy = source.top + source.height * sourcePort - bounds.top
      const tx = target.left - bounds.left,
        ty = target.top + target.height * targetPort - bounds.top
      const mid = (sx + tx) / 2
      return [
        {
          key: edge.key,
          path: `M ${sx} ${sy} C ${mid} ${sy}, ${mid} ${ty}, ${tx - 3} ${ty}`,
          x: tx - 21,
          y: ty - 16,
          number: index + 1,
        },
      ]
    }
    // Narrow layouts reserve a left gutter: the shared source branches to each
    // actual target. No line is drawn between same-stage siblings.
    const sx = source.left + 16 - bounds.left,
      sy = source.bottom - bounds.top
    const tx = target.left - bounds.left,
      ty = target.top + target.height * targetPort - bounds.top
    const lane = Math.max(9, source.left - bounds.left - 26)
    return [
      {
        key: edge.key,
        path: `M ${sx} ${sy} V ${sy + 12} H ${lane} V ${ty} H ${tx - 3}`,
        x: tx - 16,
        y: ty - 16,
        number: index + 1,
      },
    ]
  })
}
let observer: ResizeObserver | undefined
watch(
  () => props.graph,
  async () => {
    await nextTick()
    draw()
  },
  { deep: true },
)
onMounted(() => {
  observer = new ResizeObserver(draw)
  if (plot.value) observer.observe(plot.value)
  draw()
})
onUnmounted(() => observer?.disconnect())
</script>

<template>
  <div class="evolution-graph" data-evolution-graph>
    <div ref="plot" class="evolution-plot" :style="{ '--evolution-columns': layers.length }">
      <svg
        class="evolution-lines"
        :viewBox="`0 0 ${canvas.width} ${canvas.height}`"
        aria-hidden="true"
      >
        <defs>
          <marker
            :id="markerId"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill="#718796" />
          </marker>
        </defs>
        <g v-for="curve in curves" :key="curve.key">
          <path
            :d="curve.path"
            fill="none"
            stroke="#718796"
            stroke-width="2"
            :marker-end="`url(#${markerId})`"
          />
          <circle :cx="curve.x" :cy="curve.y" r="9" fill="#fff" stroke="#718796" />
          <text :x="curve.x" :y="curve.y + 4" text-anchor="middle" fill="#344554" font-size="11">
            {{ curve.number }}
          </text>
        </g>
      </svg>
      <div v-for="(layer, index) in layers" :key="index" class="evolution-layer">
        <NuxtLink
          v-for="node in layer"
          :key="node.key"
          :to="navigation.relatedLocation(node)"
          :aria-label="`${formatDexNumber(node.displayNumber)} ${node.label}`"
          class="evolution-node"
          :class="{ 'evolution-node--current': node.isCurrent }"
          :aria-current="node.isCurrent ? 'true' : undefined"
          :data-evolution-node="node.key"
        >
          <NuxtImg
            v-if="node.spriteUrl"
            :src="node.spriteUrl"
            :alt="node.label"
            width="80"
            height="80"
            loading="lazy"
            class="evolution-node__image"
          />
          <span v-else class="evolution-node__missing" aria-hidden="true">?</span>
          <span class="evolution-node__text">
            <span class="evolution-node__number">{{ formatDexNumber(node.displayNumber) }}</span>
            <strong>{{ node.label }}</strong>
            <span v-if="node.isCurrent" class="evolution-node__current">{{
              zh ? '当前形态' : 'Selected form'
            }}</span>
          </span>
        </NuxtLink>
      </div>
    </div>
    <div class="evolution-edge-list">
      <div
        v-for="edge in methods"
        :key="edge.key"
        class="evolution-edge"
        :data-evolution-edge="edge.key"
        :data-source="edge.source"
        :data-target="edge.target"
      >
        <p class="evolution-edge__route">
          <span class="evolution-edge__number">{{ edge.number }}</span>
          {{ edge.sourceNode?.label }} → {{ edge.targetNode?.label }}
        </p>
        <details :open="edge.methods.length <= 2" class="evolution-methods">
          <summary>
            {{ zh ? '进化条件' : 'Evolution conditions' }} · {{ edge.methods.length }}
            {{ zh ? '种可选途径' : 'alternative methods' }}
          </summary>
          <div
            v-for="(method, index) in edge.methods"
            :key="index"
            class="evolution-method"
            data-evolution-method
          >
            <p class="evolution-method__label">
              {{ zh ? '途径' : 'Method' }} {{ index + 1 }} · {{ zh ? '同时满足' : 'All required' }}
            </p>
            <ul>
              <li
                v-for="condition in edge.methodExplanations?.[index]?.conditions || [
                  zh ? '特殊条件待解释' : 'Special condition awaiting explanation',
                ]"
                :key="condition"
              >
                {{ condition }}
              </li>
            </ul>
            <template v-if="edge.methodExplanations?.[index]">
              <div class="evolution-method__metadata">
                <span class="evolution-method__origin" data-explanation-origin>
                  {{ zh ? '项目条件释义' : 'Project condition explanation' }}
                </span>
                <span
                  v-if="
                    edge.methodExplanations[index]!.triggerNameOrigin === 'upstream-translation'
                  "
                >
                  {{ zh ? '触发名采用上游中文' : 'Trigger name from upstream' }}
                </span>
                <span v-if="edge.methodExplanations[index]!.versionLabel" data-evolution-version>
                  {{ zh ? '引入版本：' : 'Introduced in: '
                  }}{{ edge.methodExplanations[index]!.versionLabel }}
                </span>
                <span
                  v-if="edge.methodExplanations[index]!.isDefault != null"
                  :title="
                    zh
                      ? '数据源的预期进化方式标记，不代表概率、唯一途径或当前默认形态'
                      : 'Upstream expected-evolution marker, not a probability or the only valid method'
                  "
                >
                  {{ zh ? '资料默认标记：' : 'Upstream default marker: '
                  }}{{
                    edge.methodExplanations[index]!.isDefault
                      ? zh
                        ? '是'
                        : 'yes'
                      : zh
                        ? '否'
                        : 'no'
                  }}
                </span>
              </div>
              <p
                v-for="note in edge.methodExplanations[index]!.notes"
                :key="note"
                class="evolution-method__note"
                data-evolution-note
              >
                {{ note }}
              </p>
              <aside
                v-for="supplement in edge.methodExplanations[index]!.supplements"
                :key="supplement.id"
                class="evolution-supplement"
                data-evolution-supplement
              >
                <strong>{{ zh ? '有出处的版本补充' : 'Sourced version supplement' }}</strong>
                <ul>
                  <li v-for="scope in supplement.scope" :key="scope.version_group_ids.join(',')">
                    {{ zh ? scope.zh : scope.en }}
                  </li>
                </ul>
                <p>{{ zh ? supplement.scope_note_zh : supplement.scope_note_en }}</p>
                <a :href="supplement.source_url" target="_blank" rel="noopener noreferrer"
                  >Bulbapedia</a
                >
                ·
                <a :href="supplement.corroborating_url" target="_blank" rel="noopener noreferrer"
                  >Smogon</a
                >
              </aside>
            </template>
            <details class="evolution-evidence" data-evolution-evidence>
              <summary>
                {{ zh ? '来源与原始条件（供核验）' : 'Sources and original conditions' }}
              </summary>
              <ul v-if="edge.methodExplanations?.[index]">
                <li
                  v-for="source in edge.methodExplanations[index]!.sources"
                  :key="`${source.kind}:${source.url}`"
                >
                  <a
                    v-if="source.url?.startsWith('https://')"
                    :href="source.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    >{{ source.label }}</a
                  >
                  <span v-else>{{ source.label }}</span>
                </li>
              </ul>
              <pre>{{
                JSON.stringify(
                  {
                    condition: method,
                    variables: edge.methodExplanations?.[index]?.variables || [],
                  },
                  null,
                  2,
                )
              }}</pre>
            </details>
          </div>
        </details>
      </div>
    </div>
    <p v-for="warning in visibleWarnings" :key="warning" class="evolution-graph__notice">
      {{ warning }}
    </p>
  </div>
</template>

<style scoped>
.evolution-graph {
  container-type: inline-size;
  display: grid;
  gap: 1rem;
  min-width: 0;
}
.evolution-plot {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 2.5rem;
  padding: 1rem 0.2rem 1rem 2.8rem;
}
.evolution-lines {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: visible;
}
.evolution-layer {
  display: flex;
  flex-direction: column;
  justify-content: space-evenly;
  gap: 1.5rem;
  min-width: 0;
}
.evolution-node {
  position: relative;
  display: flex;
  gap: 0.6rem;
  align-items: center;
  border: 1px solid var(--catalog-panel-line,#ccd7de);
  border-radius: 0.8rem;
  background: var(--catalog-panel-inset,#f8fafc);
  padding: 0.6rem;
  color: var(--catalog-panel-text,#1b2733);
  min-width: 0;
}
.evolution-node:hover {
  border-color: #e84a4a;
}
.evolution-node--current {
  border: 2px solid #e84a4a;
  background: var(--catalog-selected-bg,#fff6f5);
}
.evolution-node__image,
.evolution-node__missing {
  width: 4rem;
  height: 4rem;
  object-fit: contain;
  flex-shrink: 0;
}
.evolution-node__missing {
  display: grid;
  place-items: center;
  font-size: 2rem;
  color: var(--catalog-panel-muted,#667685);
}
.evolution-node__text {
  display: grid;
  gap: 0.2rem;
  min-width: 0;
  overflow-wrap: anywhere;
  font-size: 0.9rem;
}
.evolution-node__number {
  color: var(--catalog-panel-muted,#667685);
  font-size: 0.8rem;
  font-variant-numeric: tabular-nums;
}
.evolution-node__current {
  color: #b42a2a;
  font-size: 0.75rem;
}
.evolution-edge-list {
  display: grid;
  gap: 0.7rem;
}
.evolution-edge {
  padding: 0.7rem;
  border: 1px solid #dbe4ea;
  border-radius: 0.5rem;
  background: var(--catalog-panel-bg,#fff);
  overflow-wrap: anywhere;
}
.evolution-edge__route {
  font-size: 0.85rem;
  font-weight: 750;
  color: var(--catalog-panel-text,#344554);
}
.evolution-edge__number {
  display: inline-grid;
  place-items: center;
  border: 1px solid #718796;
  border-radius: 50%;
  width: 1.4rem;
  height: 1.4rem;
  margin-right: 0.3rem;
}
.evolution-methods summary {
  cursor: pointer;
  margin-top: 0.3rem;
  font-size: 0.8rem;
  color: var(--catalog-panel-muted,#667685);
}
.evolution-method {
  margin-top: 0.6rem;
  border-top: 1px solid var(--catalog-panel-line,#e4ecf0);
  padding-top: 0.5rem;
  font-size: 0.78rem;
  line-height: 1.7;
  color: var(--catalog-panel-text,#344554);
}
.evolution-method + .evolution-method::before {
  content: 'OR / 或';
  display: block;
  margin-bottom: 0.4rem;
  font-weight: 750;
  color: #b42a2a;
}
.evolution-method__label {
  font-weight: 700;
}
.evolution-method ul {
  padding-left: 1rem;
  list-style: disc;
}
.evolution-method__metadata {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.8rem;
  margin-top: 0.5rem;
  color: var(--catalog-panel-muted,#536b7d);
  font-size: 0.75rem;
}
.evolution-method__origin {
  border-radius: 0.25rem;
  background: var(--catalog-panel-inset,#eaf1f8);
  padding: 0 0.3rem;
}
.evolution-method__note,
.evolution-supplement,
.evolution-evidence {
  margin-top: 0.5rem;
  overflow-wrap: anywhere;
}
.evolution-supplement {
  border-left: 3px solid #93b9c7;
  background: var(--catalog-panel-inset,#f4f8fa);
  padding: 0.6rem;
}
.evolution-evidence pre {
  max-width: 100%;
  max-height: 20rem;
  overflow: auto;
  white-space: pre-wrap;
  font-size: 0.7rem;
}
.evolution-supplement a,
.evolution-evidence a {
  text-decoration: underline;
}
.evolution-graph__notice {
  color: var(--catalog-panel-muted,#667685);
  font-size: 0.85rem;
  line-height: 1.7;
}
@container (min-width: 640px) {
  .evolution-plot {
    display: grid;
    grid-template-columns: repeat(var(--evolution-columns), minmax(0, 1fr));
    gap: 4rem;
    padding: 1rem 0;
  }
  .evolution-node {
    flex-direction: column;
    text-align: center;
  }
}
</style>
