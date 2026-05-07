import { useQuery } from '@tanstack/react-query'
import { DigestService } from '@/client'
import { isLoggedIn } from './useAuth'

export function useTodayDigest() {
  return useQuery({
    queryKey: ['todayDigest', isLoggedIn()],
    queryFn: () => DigestService.readTodayDigest(),
    // Digest is a fixed daily artifact — don't auto-refetch on a timer.
    // Invalidate ['todayDigest'] from save/unsave/dismiss mutations so
    // the digest updates when the user's signal changes; otherwise it
    // stays stable for the day, which is the whole point of a digest.
    staleTime: Infinity,
  })
}
