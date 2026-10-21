const TOKEN_KEY = 'kc-token'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(t: string | null) {
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* privatni prozor bez skladista */
  }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(method: string, path: string, body?: unknown, form?: FormData): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined && !form) headers['Content-Type'] = 'application/json'
  const res = await fetch(path, { method, headers, body: form ?? (body !== undefined ? JSON.stringify(body) : undefined) })
  if (res.status === 401) {
    setToken(null)
    if (!location.pathname.startsWith('/prijava')) location.href = '/prijava'
  }
  if (!res.ok) {
    let msg = `Greška ${res.status}`
    try {
      const j = await res.json()
      msg = typeof j.detail === 'string' ? j.detail : msg
    } catch {
      /* nije JSON */
    }
    throw new ApiError(res.status, msg)
  }
  const ct = res.headers.get('content-type') || ''
  return (ct.includes('application/json') ? res.json() : res.blob()) as Promise<T>
}

export const api = {
  get: <T,>(p: string) => request<T>('GET', p),
  post: <T,>(p: string, b?: unknown) => request<T>('POST', p, b ?? {}),
  put: <T,>(p: string, b?: unknown) => request<T>('PUT', p, b ?? {}),
  form: <T,>(p: string, f: FormData) => request<T>('POST', p, undefined, f),
}

export async function download(path: string, filename: string) {
  const blob = await request<Blob>('GET', path)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
