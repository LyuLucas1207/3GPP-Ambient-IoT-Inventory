/** TanStack Query keys for the thesis run endpoints (one place, so invalidation stays consistent). */
export const thesisKeys = {
  all: ['thesis'] as const,
  runs: (sectionId: number | null) => ['thesis', 'runs', sectionId] as const,
  run: (runId: number | null) => ['thesis', 'run', runId] as const,
  deviceMap: (runId: number) => ['thesis', 'deviceMap', runId] as const,
  identifications: (runId: number) => ['thesis', 'identifications', runId] as const,
  rounds: (runId: number) => ['thesis', 'rounds', runId] as const,
  timeline: (runId: number | null, deviceId: number) => ['thesis', 'timeline', runId, deviceId] as const,
  roundSlots: (runId: number, roundId: number) => ['thesis', 'roundSlots', runId, roundId] as const,
  readerTimeFreq: (runId: number, readerId: number, chunk: number) => ['thesis', 'readerTimeFreq', runId, readerId, chunk] as const,
  deviceTrace: (runId: number, deviceId: number) => ['thesis', 'deviceTrace', runId, deviceId] as const,
  analysis: (runId: number, status: string) => ['thesis', 'analysis', runId, status] as const,
  snapshot: (runId: number, t: number | null) => ['thesis', 'snapshot', runId, t] as const,
}
