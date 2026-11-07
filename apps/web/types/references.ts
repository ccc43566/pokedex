export type ReferenceKind = 'items' | 'moves'

export interface CatalogLabel {
  id: number
  name: string
  localizedName: string
  nameLocale: string
  resourceType: string
  generationId?: number | null
}

export interface ReferenceCard extends CatalogLabel {
  category: CatalogLabel | null
  pocket: CatalogLabel | null
  type: CatalogLabel | null
  damageClass: CatalogLabel | null
  generation: CatalogLabel | null
  power: number | null
  accuracy: number | null
  pp: number | null
  priority: number | null
  imageUrl: string | null
  imageStatus: string | null
}

export interface ReferencePage {
  items: ReferenceCard[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}

export interface ReferenceText {
  kind: string
  version: string | null
  context: CatalogLabel | null
  locale: string
  text: string
}

export interface PriceValue {
  value: number | null
  status: 'value' | 'unavailable' | 'unknown'
}
export interface ItemPrice {
  versionGroup: CatalogLabel
  currency: CatalogLabel
  purchase: PriceValue
  sell: PriceValue
}
export interface BerryDetail {
  id: number
  itemId: number
  firmness: CatalogLabel | null
  naturalGiftType: CatalogLabel | null
  growthTime: number | null
  maxHarvest: number | null
  naturalGiftPower: number | null
  size: number | null
  smoothness: number | null
  soilDryness: number | null
  flavors: { flavor: CatalogLabel; potency: number }[]
}
export interface ReferenceFields {
  legacyCost?: number | null
  flingPower?: number | null
  flingEffect?: CatalogLabel | null
  attributes?: CatalogLabel[]
  gameIndices?: { generation: CatalogLabel; index: number }[]
  prices?: ItemPrice[]
  berry?: BerryDetail
  imageSource?: string | null
  target?: CatalogLabel | null
  effectChance?: number | null
  category?: CatalogLabel | null
  ailment?: CatalogLabel | null
  meta?: Record<string, number | string | boolean | null>
  statChanges?: { stat: CatalogLabel; change: number }[]
  pastValues?: {
    versionGroup: CatalogLabel | null
    type: CatalogLabel | null
    power: number | null
    accuracy: number | null
    pp: number | null
    effectChance: number | null
  }[]
  contestType?: CatalogLabel | null
}
export interface ReferenceDetail {
  record: ReferenceCard
  texts: ReferenceText[]
  fields: ReferenceFields
  source: { url: string; hash: string; fetchedAt: string; provider: string }
  relationCounts: Record<string, number>
}

export interface ReferenceFilters {
  'item-category'?: CatalogLabel[]
  'item-pocket'?: CatalogLabel[]
  type?: CatalogLabel[]
  'move-damage-class'?: CatalogLabel[]
  generation?: CatalogLabel[]
  'version-group'?: CatalogLabel[]
  'move-learn-method'?: CatalogLabel[]
  version?: CatalogLabel[]
  categoryPockets?: Record<string, number>
}

export interface ReferenceRelation {
  source?: {
    pokemonId?: number
    formKey?: string | null
    displayName: string
    displayNumber?: string
  } | null
  target?: {
    pokemonId?: number
    formKey?: string | null
    displayName: string
    displayNumber?: string
  } | null
  id?: number
  pokemonId?: number
  displayName?: string | null
  displayNumber?: string | null
  versionGroup?: CatalogLabel
  version?: CatalogLabel
  method?: CatalogLabel
  level?: number
  order?: number | null
  rarity?: number
  sourceOrdinal?: number[]
  itemId?: number
  moveId?: number
  itemName?: string
  moveName?: string
  chainId?: number
  path?: string
  role?: string
}
export interface RelationPage {
  items: ReferenceRelation[]
  total: number
  page: number
  pageSize: number
  totalPages: number
}
