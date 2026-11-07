import { catalogBackgrounds } from './catalogBackgrounds'
export type AppearanceMode = 'day' | 'night'
export interface AppearanceBackground {
  id: string
  mode: AppearanceMode
  name: string
  en: string
  description: string
  enDescription: string
  image: string | null
  preview: string
  mobileImage?: string
  thumbnail?: string
  base?: string
  mobileBase?: string
  aspectRatio?: number
  mobileAspectRatio?: number
  size?: string
  position?: string
  overlay?: number
}
export interface AppearancePreferences {
  mode: AppearanceMode
  backgrounds: Record<AppearanceMode, string>
  opacity: Record<AppearanceMode, number>
  dimming?: Record<string, number>
}
export const appearanceBackgrounds: AppearanceBackground[] = [
  {
    id: 'day-1',
    mode: 'day' as const,
    name: '日间 1',
    en: 'Day 1',
    description: '草野目录',
    enDescription: 'Field catalog',
    image: null,
    preview:
      'repeating-radial-gradient(circle at 100% 0,transparent 0 24px,#76947b25 24px 25px),linear-gradient(125deg,#E8EFE5,#F7F9F4 43%,#EEF4EC)',
  },
  {
    id: 'night-1',
    mode: 'night' as const,
    name: '夜间 1',
    en: 'Night 1',
    description: '观星庭院',
    enDescription: 'Stargazing courtyard',
    image: '/catalog-backgrounds/observatory-night.webp',
    overlay: 0.79,
    thumbnail: '/catalog-backgrounds/thumbs/night-1.webp',
    preview: 'url("/catalog-backgrounds/thumbs/night-1.webp") center/cover',
  },
  ...catalogBackgrounds,
]
export const recommendedOpacity: Record<AppearanceMode, number> = { day: 80, night: 88 }
export function normalizeAppearance(
  value: unknown,
  legacyOpacity: unknown = 80,
): AppearancePreferences {
  const source = value && typeof value === 'object' ? (value as Partial<AppearancePreferences>) : {}
  const number = (v: unknown, fallback: number) =>
    typeof v === 'number' && Number.isFinite(v)
      ? Math.max(0, Math.min(100, Math.round(v)))
      : fallback
  const background = (mode: AppearanceMode) =>
    appearanceBackgrounds.find((b) => b.mode === mode && b.id === source.backgrounds?.[mode])?.id ||
    appearanceBackgrounds.find((b) => b.mode === mode)!.id
  const dimming: Record<string, number> = {}
  for (const item of appearanceBackgrounds) {
    const value = source.dimming?.[item.id]
    if (typeof value === 'number' && Number.isFinite(value))
      dimming[item.id] = Math.max(0, Math.min(80, Math.round(value)))
  }
  return {
    dimming,
    mode: source.mode === 'night' ? 'night' : 'day',
    backgrounds: { day: background('day'), night: background('night') },
    opacity: {
      day: number(source.opacity?.day, number(legacyOpacity, 80)),
      night: number(source.opacity?.night, 88),
    },
  }
}
