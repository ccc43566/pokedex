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
  spriteUrl?: string | null
  artworkUrl?: string | null
  types: NamedResource[]
  generationId?: number | null
  isLegendary: boolean
  isMythical: boolean
}

export interface PaginatedPokemon {
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
  forms: PokemonFormValue[]
  evolutionChain: EvolutionNodeOut[]
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
