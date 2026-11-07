export type LocaleCode = 'zh-Hans' | 'en'

export interface NamedResource {
  id: number
  name: string
  localizedName: string
}

export interface PokemonListItem {
  id: number
  name: string
  localizedName: string
  speciesId?: number | null
  nationalDexNumber?: number | null
  variantIndex?: number | null
  isListed?: boolean
  displayNumber?: string
  variantLabel?: string
  displayName?: string
  spriteUrl?: string | null
  artworkUrl?: string | null
  types: NamedResource[]
  generationId?: number | null
  isLegendary: boolean
  isMythical: boolean
}

export interface PaginatedPokemon {
  dataVersion?: string | null
  items: PokemonListItem[]
  page: number
  pageSize: number
  total: number
  totalPages: number
  hasNext: boolean
  hasPrevious: boolean
}

export interface StatValue {
  name: string
  localizedName: string
  baseStat: number
  effort: number
}

export interface AbilityValue {
  id: number
  name: string
  localizedName: string
  effect?: string | null
  shortEffect?: string | null
  isHidden: boolean
  slot: number
}

export interface PokemonFormValue {
  id: number
  name: string
  formName?: string | null
  isDefault: boolean
  isBattleOnly: boolean
  isMega: boolean
  spriteUrl?: string | null
}

export interface EvolutionNodeOut {
  speciesId: number
  name: string
  localizedName: string
  isBaby: boolean
  condition: Record<string, unknown>
  children: EvolutionNodeOut[]
}

export interface EvolutionGraphNode {
  key: string
  speciesId: number
  pokemonId: number
  formId: number | null
  formKey: string
  name: string
  label: string
  displayNumber: string
  spriteUrl: string | null
  isCurrent: boolean
  isBaby: boolean
  query: Record<string, string>
}

export interface EvolutionGraphEdge {
  key: string
  source: string
  target: string
  methods: Record<string, unknown>[]
  methodExplanations?: EvolutionMethodExplanation[]
}

export interface EvolutionMethodExplanation {
  ruleVersion: string
  status: 'explained' | 'partial'
  conditions: string[]
  notes: string[]
  triggerLabel: string
  triggerNameOrigin: string
  versionLabel: string | null
  versionGroup: Record<string, unknown> | null
  isDefault: boolean | null
  sources: { kind: string; label: string; url: string | null; contentHash: string | null }[]
  variables: Record<string, unknown>[]
  supplements: {
    id: number
    source_url: string
    corroborating_url: string
    scope: { version_group_ids: number[]; zh: string; en: string }[]
    scope_note_zh: string
    scope_note_en: string
  }[]
  unresolved: string[]
}

export interface EvolutionGraph {
  nodes: EvolutionGraphNode[]
  edges: EvolutionGraphEdge[]
  warnings: string[]
  sourceUrl: string | null
}

export interface MediaAssetOut {
  kind: string
  url: string
  width?: number | null
  height?: number | null
}

export interface VersionSpriteOwner {
  ownerType: 'pokemon' | 'form'
  ownerId: number
  name: string
}

export interface VersionSpriteOut {
  ownerType: 'pokemon' | 'form'
  ownerId: number
  generation: string
  game: string
  kind: string
  status: 'null' | 'pending' | 'downloaded' | 'download_failed' | 'corrupt'
  format?: string | null
  sourceUrl?: string | null
  url?: string | null
  checksum?: string | null
  byteSize?: number | null
  width?: number | null
  height?: number | null
  frameCount?: number | null
}

export interface PokemonVersionMedia {
  pokemonId: number
  owners: VersionSpriteOwner[]
  sprites: VersionSpriteOut[]
}

export interface PokemonFormOption {
  key: string
  pokemonId: number
  formId?: number | null
  name: string
  label: string
  formLabel: string
  displayNumber: string
  isListed: boolean
  isDefault: boolean
  spriteUrl?: string | null
  artworkUrl?: string | null
  types: NamedResource[]
  sources: VersionSpriteOwner[]
}

export interface StatChange {
  generationId: number
  name: string
  localizedName: string
  previousName: string
  previousLocalizedName: string
  oldValue: number
  newValue: number
  isSplit: boolean
}

export interface PokemonDetail extends PokemonListItem {
  height?: number | null
  weight?: number | null
  baseExperience?: number | null
  order?: number | null
  isDefault: boolean
  description?: string | null
  genus?: string | null
  abilities: AbilityValue[]
  stats: StatValue[]
  baseStatTotal?: number
  eggGroups?: NamedResource[]
  genderRate?: number | null
  statChanges?: StatChange[]
  statHistoryAvailable?: boolean
  forms: PokemonFormValue[]
  formOptions: PokemonFormOption[]
  evolutionChain: EvolutionNodeOut[]
  evolutionGraph: EvolutionGraph
  media: MediaAssetOut[]
}

export interface TypeSummary {
  id: number
  name: string
  localizedName: string
}

export interface TypeDetail extends TypeSummary {
  damageRelations: Record<string, NamedResource[]>
  pastDamageRelations: Record<string, unknown>[]
}

export interface AbilityDetail {
  id: number
  name: string
  localizedName: string
  generationId?: number | null
  isMainSeries: boolean
  effect?: string | null
  shortEffect?: string | null
  flavorText?: string | null
}

export interface GenerationSummary {
  id: number
  name: string
  localizedName: string
  mainRegion?: string | null
  speciesCount: number
}

export interface SearchSuggestion {
  id: number
  name: string
  localizedName: string
  spriteUrl?: string | null
}
