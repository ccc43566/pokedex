import type { PokemonDetail } from '~/types/api'
export function formatDexNumber(displayNumber: number | string): string {
  return `#${displayNumber}`
}

export function typeClass(typeName: string): string {
  return `type-${typeName || 'unknown'}`
}

export function conditionSummary(condition: Record<string, unknown>): string[] {
  const labels: Record<string, string> = {
    min_level: 'Lv.',
    min_happiness: 'Friendship',
    min_affection: 'Affection',
    time_of_day: 'Time',
    location: 'Location',
    held_item: 'Held item',
    item: 'Item',
    known_move: 'Move',
    trade_species: 'Trade for',
    trigger: 'Trigger',
    version_group: 'Introduced in',
    region: 'Region',
    gender: 'Gender',
    min_beauty: 'Beauty',
    min_steps: 'Steps',
    min_move_count: 'Move uses',
    min_damage_taken: 'Damage taken',
    used_move: 'Used move',
    known_move_type: 'Known move type',
    party_type: 'Party type',
    party_species: 'Party Pokémon',
    relative_physical_stats: 'Attack / Defense',
    required_pokemon_form: 'Source form',
    evolved_pokemon_form: 'Target form',
    allowed_natures: 'Allowed natures (any)',
    condition_expression: 'Additional expression',
    needs_overworld_rain: 'Overworld rain',
    near_special_rock: 'Near special rock',
    needs_multiplayer: 'Multiplayer',
    turn_upside_down: 'Turn console upside down',
  }
  function describe(value: unknown): string {
    if (Array.isArray(value)) return value.map(describe).join(' / ')
    if (typeof value === 'object' && value) {
      if ('name' in value) return String(value.name).replace(/-/g, ' ')
      return Object.entries(value)
        .filter(([, v]) => v != null)
        .map(([k, v]) => `${k}: ${describe(v)}`)
        .join('; ')
    }
    return String(value)
  }
  const values: string[] = []
  for (const [key, value] of Object.entries(condition)) {
    if (value == null || value === false || value === '' || key === 'is_default') continue
    let text = describe(value)
    if (key === 'gender') text = value === 1 ? 'Female' : value === 2 ? 'Male' : text
    if (key === 'relative_physical_stats')
      text =
        value === 0
          ? 'Attack = Defense'
          : value === 1
            ? 'Attack > Defense'
            : value === -1
              ? 'Attack < Defense'
              : text
    values.push(`${labels[key] || key}: ${text}`)
  }
  return values
}

export function currentFormOption(pokemon: PokemonDetail, key: unknown) {
  const choices = pokemon.formOptions || []
  return (
    choices.find((item) => item.pokemonId === pokemon.id && item.key === key) ||
    choices.find((item) => item.pokemonId === pokemon.id && item.isDefault)
  )
}

export function currentPokemonName(pokemon: PokemonDetail, key: unknown): string {
  return currentFormOption(pokemon, key)?.label || pokemon.displayName || pokemon.localizedName
}
