import { useCallback, useRef } from 'react';
import { useStore } from '../store/useStore';
import { OrbTransitionEngine } from '../lib/orbTransition';
import type { OrbState } from '../lib/orbTransition';

type OrbEvent = 'START_LISTENING' | 'STOP_LISTENING' | 'START_PROCESSING' | 'START_RESPONDING' | 'FINISH' | 'ERROR' | 'RECOVER';

const fsmTable: Record<OrbState, Partial<Record<OrbEvent, OrbState>>> = {
  idle:       { START_LISTENING: 'listening', START_PROCESSING: 'processing', ERROR: 'error' },
  listening:  { STOP_LISTENING: 'processing', START_PROCESSING: 'processing', ERROR: 'error' },
  processing: { START_RESPONDING: 'responding', FINISH: 'idle', ERROR: 'error' },
  responding: { FINISH: 'idle', ERROR: 'error' },
  error:      { RECOVER: 'idle', FINISH: 'idle' },
};

/* Singleton transition engine — shared across all hook consumers */
const engine = new OrbTransitionEngine();

export function useOrbState() {
  const orbState = useStore(state => state.orbState) as OrbState;
  const setOrbState = useStore(state => state.setOrbState);
  const errorTimeoutRef = useRef<number | null>(null);

  const transition = useCallback((event: OrbEvent) => {
    const current = useStore.getState().orbState as OrbState;
    const next = fsmTable[current]?.[event];
    if (!next || next === current) return;

    // Start eased transition
    engine.startTransition(current, next);

    // Update the authoritative store state
    setOrbState(next);

    // Auto-recover from error after 3s
    if (next === 'error') {
      if (errorTimeoutRef.current) clearTimeout(errorTimeoutRef.current);
      errorTimeoutRef.current = window.setTimeout(() => {
        transition('RECOVER');
      }, 3000);
    }
  }, [setOrbState]);

  return { orbState, transition, engine };
}

export { engine as orbTransitionEngine };
export type { OrbState };
