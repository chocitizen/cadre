import { describe, expect, it } from "vitest";

import {
  assertJobTransition,
  getNextJobStates,
  isJobTransitionAllowed
} from "../../src/server/jobs/states";

describe("job state transitions", () => {
  it("supports the durable happy path", () => {
    expect(isJobTransitionAllowed("queued", "running")).toBe(true);
    expect(isJobTransitionAllowed("running", "ready")).toBe(true);
    expect(isJobTransitionAllowed("ready", "delivered")).toBe(true);
    expect(isJobTransitionAllowed("delivered", "archived")).toBe(true);
  });

  it("supports approval and review without pretending work is complete", () => {
    expect(isJobTransitionAllowed("running", "needs_approval")).toBe(true);
    expect(isJobTransitionAllowed("needs_approval", "review")).toBe(true);
    expect(isJobTransitionAllowed("review", "ready")).toBe(true);
  });

  it("rejects skipped and terminal transitions", () => {
    expect(() => assertJobTransition("queued", "ready")).toThrow("Invalid job transition");
    expect(getNextJobStates("archived")).toEqual([]);
  });
});
