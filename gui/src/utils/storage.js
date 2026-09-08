/**
 * 本地存储封装
 */
export function set(key, value) {
  if (value === null || value === undefined) {
    localStorage.removeItem(key)
  } else {
    localStorage.setItem(key, JSON.stringify(value))
  }
}

export function get(key) {
  const val = localStorage.getItem(key)
  if (val === null) return null
  try {
    return JSON.parse(val)
  } catch {
    return val
  }
}

export function remove(key) {
  localStorage.removeItem(key)
}

export function clear() {
  localStorage.clear()
}
