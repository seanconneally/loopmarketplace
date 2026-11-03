// Tab-scoped drafts contain no tokens and are removed on explicit sign-out.
export function readDraft<T>(key: string, fallback: T): T {
  try {
    return (JSON.parse(sessionStorage.getItem(key) || 'null') as T) ?? fallback;
  } catch {
    return fallback;
  }
}
export function writeDraft(key: string, value: unknown): boolean {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}
export function readTextDraft(key: string): Record<string, string> {
  const value = readDraft<unknown>(key, null);
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {};
  return Object.fromEntries(
    Object.entries(value).filter(
      ([name, text]) => name !== '__proto__' && typeof text === 'string' && text.length <= 4000,
    ),
  );
}
export function removeDraft(key: string) {
  try {
    sessionStorage.removeItem(key);
  } catch {
    /* Storage may be unavailable. */
  }
}
export function clearMemberDrafts(userId: string) {
  for (const kind of ['chat', 'advert']) removeDraft(`motorloop.${kind}-draft.${userId}`);
  removeDraft(`motorloop.chat-draft.${userId}.attempts`);
}
