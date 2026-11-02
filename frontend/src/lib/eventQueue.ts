export type ResearchEventInput = {
  event_type: string
  task_id?: string
  occurred_at?: string
  payload?: Record<string, unknown>
}

type QueuedResearchEvent = {
  session_id: string
  event_id: string
  event_type: string
  task_id?: string
  occurred_at: string
  payload: Record<string, unknown>
}

const STORAGE_KEY = 'behaviourlens.event-queue.v1'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const MAX_QUEUE_LENGTH = 5000
let memoryQueue: QueuedResearchEvent[] = []

function readQueue(): QueuedResearchEvent[] {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (!stored) return memoryQueue
    const parsed: unknown = JSON.parse(stored)
    return Array.isArray(parsed) ? (parsed as QueuedResearchEvent[]) : memoryQueue
  } catch {
    return memoryQueue
  }
}

function writeQueue(queue: QueuedResearchEvent[]) {
  memoryQueue = queue.slice(-MAX_QUEUE_LENGTH)
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(memoryQueue))
  } catch {
    // Keep the queue in memory if browser storage is unavailable or full.
  }
}

function newEventId(): string {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  const randomBytes = new Uint8Array(16)
  globalThis.crypto.getRandomValues(randomBytes)
  return Array.from(randomBytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

export function enqueueResearchEvent(sessionId: string, input: ResearchEventInput): string {
  const eventId = newEventId()
  if (!sessionId.trim() || !input.event_type.trim()) return eventId

  const event: QueuedResearchEvent = {
    session_id: sessionId,
    event_id: eventId,
    event_type: input.event_type,
    task_id: input.task_id,
    occurred_at: input.occurred_at ?? new Date().toISOString(),
    payload: input.payload ?? {},
  }
  writeQueue([...readQueue(), event])
  return eventId
}

export function getQueuedResearchEventCount(sessionId?: string): number {
  const queue = readQueue()
  return sessionId ? queue.filter((event) => event.session_id === sessionId).length : queue.length
}

export async function flushQueuedResearchEvents(sessionId: string): Promise<number> {
  if (!sessionId.trim() || typeof window === 'undefined') return 0

  let flushedCount = 0
  const sessionQueue = readQueue().filter((event) => event.session_id === sessionId)
  for (let offset = 0; offset < sessionQueue.length; offset += 500) {
    const batch = sessionQueue.slice(offset, offset + 500)
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/sessions/${encodeURIComponent(sessionId)}/events`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            events: batch.map(({ session_id: _sessionId, ...event }) => event),
          }),
        },
      )
      if (!response.ok) break

      const result: unknown = await response.json()
      if (
        !result ||
        typeof result !== 'object' ||
        !('accepted' in result) ||
        !('duplicates' in result) ||
        typeof result.accepted !== 'number' ||
        typeof result.duplicates !== 'number' ||
        result.accepted + result.duplicates !== batch.length
      ) {
        break
      }

      const flushedIds = new Set(batch.map((event) => event.event_id))
      writeQueue(
        readQueue().filter(
          (event) => event.session_id !== sessionId || !flushedIds.has(event.event_id),
        ),
      )
      flushedCount += batch.length
    } catch {
      break
    }
  }

  return flushedCount
}