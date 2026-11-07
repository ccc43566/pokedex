export function useReferenceText() {
  const { locale } = useI18n()
  const tr = (zh: string, en: string) => (locale.value === 'zh-Hans' ? zh : en)
  const value = (v: number | string | boolean | null | undefined) =>
    v == null ? tr('未提供', 'Not provided') : String(v)
  return { tr, value }
}
