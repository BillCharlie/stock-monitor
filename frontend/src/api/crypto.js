// Two-layer key protection:
// 1. localStorage: XOR-obfuscated + Base64  (prevents casual devtools reading)
// 2. Wire: SHA-256 hash only  (plaintext key never leaves the browser)

const OBF_SEED = 'sm-v1-xk-2026'

function xorStr(str, seed) {
  return str.split('').map((c, i) =>
    String.fromCharCode(c.charCodeAt(0) ^ seed.charCodeAt(i % seed.length))
  ).join('')
}

/** Obfuscate before writing to localStorage */
export function obfuscate(plain) {
  if (!plain) return ''
  try {
    return btoa(xorStr(plain, OBF_SEED))
  } catch {
    return plain
  }
}

/** Deobfuscate after reading from localStorage */
export function deobfuscate(stored) {
  if (!stored) return ''
  try {
    return xorStr(atob(stored), OBF_SEED)
  } catch {
    return stored // fallback: treat as plain text (legacy)
  }
}

/** SHA-256 hex digest — sent as X-API-Secret header instead of plaintext */
export async function hashKey(plain) {
  if (!plain) return ''
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(plain))
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('')
}
