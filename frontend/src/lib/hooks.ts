import { useQuery } from '@tanstack/react-query'
import { api } from './api'
import type { Codebooks, Unit } from './types'

export function useUnits() {
  return useQuery({ queryKey: ['units'], queryFn: () => api.get<(Unit & { description: string; email: string; active: boolean })[]>('/api/admin/units'), staleTime: 60000 })
}

export function useCodebooks() {
  return useQuery({ queryKey: ['codebooks'], queryFn: () => api.get<Codebooks>('/api/admin/codebooks'), staleTime: 60000 })
}

export function useCategories() {
  const { data } = useCodebooks()
  return (data?.kategorija ?? []).map((c) => ({ code: c.code, label: c.label, unit: c.data.unit as string }))
}
