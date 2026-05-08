import { useQuery } from '@tanstack/react-query'
import { DigestService } from '@/client'
import { isLoggedIn } from './useAuth'

export function useTodayDigest() {
  return useQuery({
    queryKey: ['todayDigest', isLoggedIn()],
    queryFn: () => DigestService.readTodayDigest(),
    // Digest is a fixed daily artifact — don't auto-refetch on a timer.
    // Dismiss can still invalidate ['todayDigest'] when the user explicitly
    // removes an item, but saving articles should not reshuffle this surface.
    staleTime: Infinity,
  })
}
