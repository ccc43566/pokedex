import {
  appearanceBackgrounds,
  normalizeAppearance,
  type AppearanceMode,
  type AppearancePreferences,
} from '~/utils/appearance'

export function useAppearance() {
  const legacy = useCookie<number>('pokemon-card-background-opacity')
  const saved = useCookie<AppearancePreferences>('pokedex-appearance-v1', {
    default: () => normalizeAppearance(null, legacy.value),
    sameSite: 'lax',
    maxAge: 60 * 60 * 24 * 365,
  })
  const preferences = computed(() => normalizeAppearance(saved.value, legacy.value))
  const mode = computed(() => preferences.value.mode)
  const background = computed(() =>
    appearanceBackgrounds.find((b) => b.id === preferences.value.backgrounds[mode.value])!,
  )
  function setMode(value: AppearanceMode) {
    saved.value = { ...preferences.value, mode: value }
  }
  function setBackground(id: string) {
    const candidate = appearanceBackgrounds.find((b) => b.id === id && b.mode === mode.value)
    if (candidate)
      saved.value = {
        ...preferences.value,
        backgrounds: { ...preferences.value.backgrounds, [mode.value]: id },
      }
  }
  const cardOpacity = computed({
    get: () => preferences.value.opacity[mode.value],
    set: (value: number) => {
      if (!Number.isFinite(value)) return
      saved.value = {
        ...preferences.value,
        opacity: {
          ...preferences.value.opacity,
          [mode.value]: Math.max(0, Math.min(100, Math.round(value))),
        },
      }
    },
  })
  const backgroundDimming = computed({
    get: () =>
      preferences.value.dimming?.[background.value.id] ??
      Math.round((background.value.overlay ?? 0.12) * 100),
    set: (value: number) => {
      if (!Number.isFinite(value)) return
      saved.value = {
        ...preferences.value,
        dimming: {
          ...preferences.value.dimming,
          [background.value.id]: Math.max(0, Math.min(80, Math.round(value))),
        },
      }
    },
  })
  return { preferences, mode, background, cardOpacity, backgroundDimming, setMode, setBackground }
}
