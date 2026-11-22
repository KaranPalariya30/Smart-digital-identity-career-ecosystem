// SHA-256 in the browser, formatted exactly like blockchain-service/app/hashing.py:
// "0x" + 64 lowercase hex characters. If this matches the server's document_hash,
// the file the student sees is byte-for-byte the file that was registered.
export const hashSupported = typeof crypto !== 'undefined' && !!crypto.subtle

export async function sha256Hex(input) {
  if (!hashSupported) throw new Error('Hashing needs a secure context (https or localhost).')
  const bytes = typeof input === 'string' ? new TextEncoder().encode(input)
    : input instanceof ArrayBuffer ? input : await input.arrayBuffer()
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return '0x' + [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('')
}

export const sameHash = (a, b) => !!a && !!b && a.toLowerCase() === b.toLowerCase()
