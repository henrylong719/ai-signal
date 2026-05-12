import { useCallback, useRef } from 'react'
import { useIsMobile } from '@/hooks/useMobile'

interface UseSwipeTabsOptions<T extends string> {
  /**
   * Ordered list of tab values. Swipe-left moves toward the end of the
   * array; swipe-right moves toward the start. The list does not wrap.
   */
  tabs: readonly T[]
  activeTab: T
  onChangeTab: (tab: T) => void
  /**
   * Caller-level toggle, ANDed with the internal mobile check. Defaults
   * to true. Pass false to skip swipe entirely (e.g. inside a region
   * that owns horizontal gestures).
   */
  enabled?: boolean
  /** Minimum horizontal distance (px) before a swipe is committed. */
  threshold?: number
}

interface SwipeHandlers {
  onTouchStart: (event: React.TouchEvent) => void
  onTouchMove: (event: React.TouchEvent) => void
  onTouchEnd: (event: React.TouchEvent) => void
  onTouchCancel: (event: React.TouchEvent) => void
}

interface GestureState {
  startX: number
  startY: number
  // Once movement passes the disambiguation distance we lock the
  // gesture to an axis: 'vertical' means the user is scrolling and we
  // ignore the rest of the touch; 'horizontal' means a swipe is in
  // progress and onTouchEnd will decide whether to change tabs.
  locked: 'none' | 'horizontal' | 'vertical'
  active: boolean
}

// Movement (px) before we decide whether the gesture is a vertical
// scroll or a horizontal swipe. Small enough to feel responsive,
// large enough to avoid jitter from a stationary tap.
const AXIS_LOCK_DISTANCE = 10

/**
 * Reusable touch handlers for primary page-level tabs. Returns an
 * object suitable for spreading onto the element that wraps the tab
 * panel content.
 *
 * Behavior:
 * - No-op unless we're on a mobile-sized viewport (Tailwind `md`
 *   breakpoint) and `enabled` is true.
 * - Horizontal movement must clearly exceed vertical movement and
 *   pass `threshold` before a tab change is committed — vertical
 *   scrolling locks the gesture out for the remainder of the touch.
 * - Does not wrap: swiping past the first/last tab is a no-op.
 * - Single-touch only; multi-touch gestures (e.g. pinch) are ignored.
 */
export function useSwipeTabs<T extends string>({
  tabs,
  activeTab,
  onChangeTab,
  enabled = true,
  threshold = 60,
}: UseSwipeTabsOptions<T>): SwipeHandlers {
  const isMobile = useIsMobile()
  const isEnabled = enabled && isMobile

  const stateRef = useRef<GestureState>({
    startX: 0,
    startY: 0,
    locked: 'none',
    active: false,
  })

  const onTouchStart = useCallback(
    (event: React.TouchEvent) => {
      if (!isEnabled || event.touches.length !== 1) {
        stateRef.current.active = false
        return
      }
      const touch = event.touches[0]
      stateRef.current = {
        startX: touch.clientX,
        startY: touch.clientY,
        locked: 'none',
        active: true,
      }
    },
    [isEnabled],
  )

  const onTouchMove = useCallback(
    (event: React.TouchEvent) => {
      const state = stateRef.current
      if (!isEnabled || !state.active || state.locked !== 'none') {
        return
      }
      if (event.touches.length !== 1) {
        state.active = false
        return
      }

      const touch = event.touches[0]
      const absX = Math.abs(touch.clientX - state.startX)
      const absY = Math.abs(touch.clientY - state.startY)

      if (absX < AXIS_LOCK_DISTANCE && absY < AXIS_LOCK_DISTANCE) {
        return
      }
      state.locked = absY > absX ? 'vertical' : 'horizontal'
    },
    [isEnabled],
  )

  const onTouchEnd = useCallback(
    (event: React.TouchEvent) => {
      const state = stateRef.current
      if (!isEnabled || !state.active) {
        state.active = false
        return
      }
      state.active = false

      if (state.locked === 'vertical') {
        return
      }

      const touch = event.changedTouches[0]
      if (!touch) {
        return
      }
      const deltaX = touch.clientX - state.startX
      const deltaY = touch.clientY - state.startY
      const absX = Math.abs(deltaX)
      const absY = Math.abs(deltaY)

      if (absX < threshold || absX <= absY) {
        return
      }

      const currentIndex = tabs.indexOf(activeTab)
      if (currentIndex === -1) {
        return
      }
      const nextIndex = deltaX < 0 ? currentIndex + 1 : currentIndex - 1
      if (nextIndex < 0 || nextIndex >= tabs.length) {
        return
      }
      onChangeTab(tabs[nextIndex])
    },
    [isEnabled, threshold, tabs, activeTab, onChangeTab],
  )

  const onTouchCancel = useCallback(() => {
    stateRef.current.active = false
    stateRef.current.locked = 'none'
  }, [])

  return { onTouchStart, onTouchMove, onTouchEnd, onTouchCancel }
}
