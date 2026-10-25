export function formatDexNumber(id: number): string {
  return `#${String(id).padStart(4, '0')}`
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
  }
  const values: string[] = []
  for (const [key, value] of Object.entries(condition)) {
    if (value === null || value === false) continue
    if (key === 'trigger' || key === 'version_group') continue
    if (typeof value === 'object' && value && 'name' in value) {
      values.push(`${labels[key] || key}: ${String((value as { name: unknown }).name)}`)
    } else if (typeof value !== 'object') {
      values.push(`${labels[key] || key}: ${String(value)}`)
    }
  }
  return values
}
