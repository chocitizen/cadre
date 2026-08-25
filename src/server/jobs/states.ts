export const JOB_STATES = [
  "queued",
  "running",
  "needs_approval",
  "review",
  "ready",
  "failed",
  "delivered",
  "archived"
] as const;

export type JobState = (typeof JOB_STATES)[number];

const JOB_TRANSITIONS: Readonly<Record<JobState, readonly JobState[]>> = {
  queued: ["running", "needs_approval", "failed", "archived"],
  running: ["needs_approval", "review", "ready", "failed"],
  needs_approval: ["queued", "review", "failed", "archived"],
  review: ["needs_approval", "ready", "failed", "archived"],
  ready: ["delivered", "archived"],
  failed: ["queued", "archived"],
  delivered: ["archived"],
  archived: []
};

export function isJobState(value: string): value is JobState {
  return JOB_STATES.some((state) => state === value);
}

export function getNextJobStates(state: JobState): readonly JobState[] {
  return JOB_TRANSITIONS[state];
}

export function isJobTransitionAllowed(currentState: JobState, nextState: JobState): boolean {
  return JOB_TRANSITIONS[currentState].includes(nextState);
}

export function assertJobTransition(currentState: JobState, nextState: JobState): void {
  if (!isJobTransitionAllowed(currentState, nextState)) {
    throw new Error(`Invalid job transition: ${currentState} -> ${nextState}`);
  }
}
