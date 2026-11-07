import { typePalette } from './typePalette'

export interface PresentedType {
  id: number
  name: string
  localizedName: string
}
export function isVisibleType(type: Pick<PresentedType, 'name'> | null | undefined): boolean {
  return Boolean(type?.name && type.name !== 'shadow' && type.name !== 'unknown')
}
export function typeColors(name: string) {
  return typePalette[name] || { icon: '#B9BCA9', label: '#959689' }
}
