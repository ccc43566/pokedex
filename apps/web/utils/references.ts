import type { PriceValue } from '~/types/references'

export function formatPrice(price: PriceValue, purchase: boolean, chinese: boolean): string {
  if (price.status === 'value' && price.value != null) return String(price.value)
  if (price.status === 'unavailable') {
    return chinese
      ? purchase
        ? '不可购买'
        : '不可出售'
      : purchase
        ? 'Not purchasable'
        : 'Not sellable'
  }
  return chinese ? '未提供' : 'Not provided'
}

export function readableIdentifier(value: string): string {
  return value.replace(/[-_]/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}
