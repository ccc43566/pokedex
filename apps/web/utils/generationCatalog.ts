// National Pokédex ranges classify forms with their original species.
export const generationCatalog = [
  { id: 1, numeral: '一', start: 1, end: 151, starters: [1, 4, 7] },
  { id: 2, numeral: '二', start: 152, end: 251, starters: [152, 155, 158] },
  { id: 3, numeral: '三', start: 252, end: 386, starters: [252, 255, 258] },
  { id: 4, numeral: '四', start: 387, end: 493, starters: [387, 390, 393] },
  { id: 5, numeral: '五', start: 494, end: 649, starters: [495, 498, 501] },
  { id: 6, numeral: '六', start: 650, end: 721, starters: [650, 653, 656] },
  { id: 7, numeral: '七', start: 722, end: 809, starters: [722, 725, 728] },
  { id: 8, numeral: '八', start: 810, end: 905, starters: [810, 813, 816] },
  { id: 9, numeral: '九', start: 906, end: 1025, starters: [906, 909, 912] },
] as const

export type GenerationEntry = (typeof generationCatalog)[number]

export function generationRange(generation: GenerationEntry): string {
  return `#${String(generation.start).padStart(3, '0')}–${generation.end}`
}
