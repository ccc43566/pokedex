// Shared bounded LRU primitive. Callers decide SSR scope and expiry policy.
export function createListCache<T>(capacity = 3, dispose?: (value: T) => void) {
  const values = new Map<string, T>()
  function remove(key: string) {
    const value = values.get(key)
    values.delete(key)
    if (value !== undefined) dispose?.(value)
  }
  function get(key: string): T | undefined {
    const value = values.get(key)
    if (value !== undefined) {
      values.delete(key)
      values.set(key, value)
    }
    return value
  }
  function set(key: string, value: T) {
    values.delete(key)
    values.set(key, value)
    while (values.size > capacity) remove(values.keys().next().value!)
  }
  return { get, set, remove }
}
