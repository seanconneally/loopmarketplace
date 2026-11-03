import { mutation, request } from '../../api/client';

type Signal = {
  client_event_id: string;
  listing_id: string;
  event_type: 'watch' | 'impression' | 'completion' | 'replay';
  value: number;
  occurred_at: string;
};
let owner: string | null = null;
let generation = 0;
let queue: Signal[] = [];
let sending: Promise<void> | null = null;
const samplers = new Set<() => void>();

export function setSignalOwner(value: string | null) {
  if (owner !== value) {
    clearSignals();
    owner = value;
  }
}
export const signalGeneration = () => generation;
export function clearSignals() {
  generation++;
  queue = [];
}
export function registerSampler(sample: () => void) {
  samplers.add(sample);
  return () => {
    samplers.delete(sample);
  };
}
export function signal(
  user: string,
  listing: string,
  event_type: Signal['event_type'],
  value: number,
) {
  if (user !== owner) return;
  queue.push({
    client_event_id: crypto.randomUUID(),
    listing_id: listing,
    event_type,
    value,
    occurred_at: new Date().toISOString(),
  });
  queue = queue.slice(-100);
}
export async function flushSignals() {
  for (const sample of samplers) sample();
  if (sending) await sending;
  if (!owner || !queue.length) return;
  queue = queue.filter((event) => Date.now() - Date.parse(event.occurred_at) < 60000);
  if (!queue.length) return;
  const events = queue.splice(0),
    version = generation;
  sending = request(
    '/analytics/events',
    {
      ...mutation({ events }),
      signal: AbortSignal.timeout(2500),
    },
    false,
  )
    .then(() => undefined)
    .catch(() => {
      if (version === generation) queue = [...events, ...queue].slice(-100);
    })
    .finally(() => {
      sending = null;
    });
  await sending;
}
