export type OrbState = 'idle' | 'listening' | 'processing' | 'responding' | 'error';

export interface TransitionState {
  from: OrbState;
  to: OrbState;
  progress: number;      // 0.0 → 1.0
  phase: 'none' | 'exit' | 'enter';
  startTime: number;
}

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

export class OrbTransitionEngine {
  private state: TransitionState = {
    from: 'idle',
    to: 'idle',
    progress: 1.0,
    phase: 'none',
    startTime: 0
  };

  private duration: number = 500;
  private exitRatio: number = 0.4;

  /**
   * Start a new transition between two orb states.
   * Duration varies by transition pair.
   */
  startTransition(from: OrbState, to: OrbState): void {
    // Determine duration based on transition pair
    if (from === 'listening' && to === 'processing') {
      this.duration = 800; // has collapse beat
    } else if (from === 'processing' && to === 'responding') {
      this.duration = 600;
    } else if (from === 'responding' && to === 'idle') {
      this.duration = 1500; // slow wind-down
    } else {
      this.duration = 500;
    }

    this.state = {
      from,
      to,
      progress: 0,
      phase: 'exit',
      startTime: performance.now()
    };
  }

  /**
   * Call each frame. Calculates progress from elapsed time,
   * applies easeInOutCubic, and determines the current phase.
   */
  update(): TransitionState {
    if (this.state.progress >= 1.0) {
      return this.state;
    }

    const elapsed = performance.now() - this.state.startTime;
    const rawProgress = Math.min(elapsed / this.duration, 1.0);
    const easedProgress = easeInOutCubic(rawProgress);

    this.state = {
      ...this.state,
      progress: easedProgress,
      phase: easedProgress < this.exitRatio ? 'exit' : (easedProgress < 1.0 ? 'enter' : 'none')
    };

    return this.state;
  }

  /** Returns true if the transition is still in progress. */
  get isTransitioning(): boolean {
    return this.state.progress < 1.0;
  }

  /**
   * Returns the visual state to render:
   * `from` during exit phase, `to` during enter phase.
   */
  get currentVisualState(): OrbState {
    return this.state.progress < this.exitRatio ? this.state.from : this.state.to;
  }

  /**
   * 0→1 value representing how "active" the visual should be.
   * During exit phase: fades from 1→0.3.
   * During enter phase: ramps from 0.3→1.
   * Drives signal spawn rates and node brightness.
   */
  get visualIntensity(): number {
    if (this.state.progress >= 1.0) {
      return 1.0;
    }

    if (this.state.progress < this.exitRatio) {
      // Exit phase: fade from 1 → 0.3
      const exitProgress = this.state.progress / this.exitRatio;
      return 1.0 - (0.7 * exitProgress); // 1.0 → 0.3
    } else {
      // Enter phase: ramp from 0.3 → 1
      const enterProgress = (this.state.progress - this.exitRatio) / (1.0 - this.exitRatio);
      return 0.3 + (0.7 * enterProgress); // 0.3 → 1.0
    }
  }

  /**
   * True only during `listening → processing` exit phase.
   * Signals should converge inward (collapse beat).
   */
  get collapseActive(): boolean {
    return (
      this.state.from === 'listening' &&
      this.state.to === 'processing' &&
      this.state.phase === 'exit'
    );
  }

  /**
   * True only during `processing → responding` enter phase.
   * Signals should burst outward (radiate).
   */
  get radiateActive(): boolean {
    return (
      this.state.from === 'processing' &&
      this.state.to === 'responding' &&
      this.state.phase === 'enter'
    );
  }
}
