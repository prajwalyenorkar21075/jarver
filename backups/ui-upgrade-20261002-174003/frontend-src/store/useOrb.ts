import { create } from 'zustand'
import type { OrbState } from 'thinking-orbs'

export const ORB_STATES: OrbState[] = [
  'working',
  'searching',
  'solving',
  'listening',
  'connecting',
  'weaving',
  'composing',
  'breathing',
  'shaping',
]

interface OrbStore {
  state: OrbState
  setState: (s: OrbState) => void
}

export const useOrb = create<OrbStore>((set) => ({
  state: 'searching',
  setState: (state) => set({ state }),
}))
