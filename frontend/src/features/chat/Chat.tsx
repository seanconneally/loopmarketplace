import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import {
  CalendarDays,
  Download,
  Flag,
  MessageCircle,
  Send,
  ShieldCheck,
  UserX,
  ArrowLeft,
} from 'lucide-react';
import {
  downloadCalendar,
  mutation,
  request,
  type Conversation,
  type Message,
  type Viewing,
} from '../../api/client';
import { useAuth } from '../../shared/Auth';
import { Modal } from '../../shared/Modal';
import { PageHeading } from '../../shared/PageHeading';
import { readDraft, readTextDraft, writeDraft } from '../../shared/draftStorage';
import { useOnlineStatus } from '../../shared/useOnlineStatus';

export function Chat({ initialConversation }: { initialConversation?: string | null }) {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string | null>(initialConversation || null);
  const online = useOnlineStatus();
  const draftKey = `motorloop.chat-draft.${auth.user?.id}`;
  const [drafts, setDrafts] = useState<Record<string, string>>(() => readTextDraft(draftKey));
  const [draftWarning, setDraftWarning] = useState(false);
  useEffect(() => {
    setDraftWarning(!writeDraft(draftKey, drafts));
  }, [draftKey, drafts]);
  const body = selected ? drafts[selected] || '' : '';
  const attempts = useRef(
    new Map(
      Object.entries(
        readDraft<Record<string, { body: string; key: string }>>(draftKey + '.attempts', {}),
      ).filter(
        ([, value]) => value && typeof value.body === 'string' && typeof value.key === 'string',
      ),
    ),
  );
  const [proposal, setProposal] = useState(false);
  const [proposing, setProposing] = useState(false);
  const proposalAttempt = useRef<{ fingerprint: string; key: string } | null>(null);
  const [counter, setCounter] = useState<Viewing | null>(null);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [reportReason, setReportReason] = useState('');
  const conversations = useInfiniteQuery({
    queryKey: ['conversations', auth.user?.id],
    initialPageParam: '',
    queryFn: ({ pageParam }) =>
      request<{ items: Conversation[]; next_cursor: string | null }>(
        `/conversations${pageParam ? `?cursor=${encodeURIComponent(pageParam)}` : ''}`,
      ),
    getNextPageParam: (page) => page.next_cursor || undefined,
    enabled: !!auth.user,
  });
  const conversationItems = [
    ...new Map(
      (conversations.data?.pages.flatMap((page) => page.items) || []).map((item) => [
        item.id,
        item,
      ]),
    ).values(),
  ];
  const conversation = conversationItems.find((item) => item.id === selected);
  const messages = useInfiniteQuery({
    queryKey: ['messages', selected],
    initialPageParam: '',
    queryFn: ({ pageParam }) =>
      request<{ items: Message[]; next_cursor: string | null }>(
        `/conversations/${selected}/messages${pageParam ? `?cursor=${encodeURIComponent(pageParam)}` : ''}`,
      ),
    getNextPageParam: (page) => page.next_cursor || undefined,
    enabled: !!selected,
    refetchInterval: 10000,
  });
  const messageItems = [
    ...new Map(
      (
        messages.data?.pages
          .slice()
          .reverse()
          .flatMap((page) => page.items) || []
      ).map((item) => [item.id, item]),
    ).values(),
  ];
  const viewings = useInfiniteQuery({
    queryKey: ['viewings', selected],
    initialPageParam: '',
    queryFn: ({ pageParam }) =>
      request<{ items: Viewing[]; next_cursor: string | null }>(
        `/viewings?conversation_id=${selected}${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ''}`,
      ),
    getNextPageParam: (page) => page.next_cursor || undefined,
    enabled: !!selected,
    refetchInterval: 10000,
  });
  useEffect(() => {
    if (initialConversation) setSelected(initialConversation);
  }, [initialConversation]);
  useEffect(() => {
    const last = messages.data?.pages[0]?.items.at(-1);
    if (last && !last.read_at && last.sender_id !== auth.user?.id)
      void request(`/conversations/${selected}/read`, {
        method: 'PUT',
        body: JSON.stringify({ message_id: last.id }),
      }).catch(() => undefined);
  }, [messages.data, auth.user?.id, selected]);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!body.trim() || !selected || sending || !online) return;
    setSending(true);
    setError('');
    const conversationId = selected;
    const submitted = body;
    let attempt = attempts.current.get(conversationId);
    if (!attempt || attempt.body !== submitted) {
      attempt = { body: submitted, key: crypto.randomUUID() };
      attempts.current.set(conversationId, attempt);
      writeDraft(draftKey + '.attempts', Object.fromEntries(attempts.current));
    }
    try {
      await request(
        `/conversations/${conversationId}/messages`,
        mutation({ body: submitted }, attempt.key),
      );
      attempts.current.delete(conversationId);
      writeDraft(draftKey + '.attempts', Object.fromEntries(attempts.current));
      setDrafts((current) =>
        current[conversationId] === submitted ? { ...current, [conversationId]: '' } : current,
      );
      await queryClient.invalidateQueries({ queryKey: ['messages', conversationId] });
      await queryClient.invalidateQueries({ queryKey: ['conversations'] });
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setSending(false);
    }
  }
  async function respond(viewing: Viewing, action: string) {
    try {
      await request(
        `/viewings/${viewing.id}/respond`,
        mutation({ revision: viewing.revision, action }),
      );
      await queryClient.invalidateQueries({ queryKey: ['viewings', selected] });
      await queryClient.invalidateQueries({ queryKey: ['messages', selected] });
    } catch (problem) {
      setError((problem as Error).message);
    }
  }
  async function propose(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (proposing || !selected || !online) return;
    setProposing(true);
    setError('');
    const conversationId = selected;
    const values = new FormData(event.currentTarget);
    try {
      const details = {
        starts_at: new Date(String(values.get('time'))).toISOString(),
        place: String(values.get('place')),
      };
      const path = counter ? `/viewings/${counter.id}/respond` : '/viewings';
      const payload = counter
        ? { ...details, action: 'counter', revision: counter.revision }
        : { ...details, conversation_id: conversationId };
      const fingerprint = JSON.stringify({ path, payload });
      if (proposalAttempt.current?.fingerprint !== fingerprint)
        proposalAttempt.current = { fingerprint, key: crypto.randomUUID() };
      await request(path, mutation(payload, proposalAttempt.current.key));
      proposalAttempt.current = null;
      setProposal(false);
      setCounter(null);
      await queryClient.invalidateQueries({ queryKey: ['viewings', conversationId] });
      await queryClient.invalidateQueries({ queryKey: ['messages', conversationId] });
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setProposing(false);
    }
  }
  async function block() {
    if (!conversation || !auth.user) return;
    try {
      const other =
        conversation.buyer_id === auth.user.id ? conversation.seller_id : conversation.buyer_id;
      await request('/moderation/blocks', {
        method: 'PUT',
        body: JSON.stringify({ user_id: other }),
      });
      setSelected(null);
      await queryClient.invalidateQueries({ queryKey: ['conversations'] });
      await queryClient.invalidateQueries({ queryKey: ['feed'] });
    } catch (problem) {
      setError((problem as Error).message);
    }
  }

  return (
    <>
      <PageHeading
        eyebrow="START WITH A CONVERSATION"
        title={
          <>
            Good questions. <span>Better connections.</span>
          </>
        }
        description="Ask about the details, agree a time and keep everything in one place."
        action={
          <span className="section-pill">
            <ShieldCheck size={16} />
            Private conversations
          </span>
        }
      />
      <div className={`chat-layout ${selected ? 'has-conversation' : ''}`}>
        <aside className="conversation-list">
          <div className="panel-kicker">CONVERSATIONS</div>
          {conversations.isPending && <p className="muted">Loading conversations…</p>}
          {conversations.error && <p className="error">{conversations.error.message}</p>}
          {conversationItems.map((item) => (
            <button
              key={item.id}
              className={`conversation-item ${selected === item.id ? 'active' : ''}`}
              onClick={() => setSelected(item.id)}
            >
              <div className="seller-avatar">{item.other_name.slice(0, 2).toUpperCase()}</div>
              <div>
                <strong>{item.other_name}</strong>
                <span>{item.listing_title}</span>
              </div>
            </button>
          ))}
          {conversations.hasNextPage && (
            <button
              className="text-button"
              disabled={conversations.isFetchingNextPage}
              onClick={() => void conversations.fetchNextPage()}
            >
              {conversations.isFetchingNextPage ? 'Loading…' : 'More conversations'}
            </button>
          )}
          {conversations.isSuccess && conversationItems.length === 0 && (
            <p className="muted">Find a listing you like and message its seller to get started.</p>
          )}
        </aside>
        <section className="chat-panel">
          {!selected ? (
            <div className="chat-placeholder">
              <MessageCircle size={42} />
              <h2>Your next conversation starts here.</h2>
              <p>Choose a conversation, or find a listing and message its seller.</p>
            </div>
          ) : (
            <>
              <header className="chat-header">
                <button
                  className="icon-button chat-back"
                  aria-label="All conversations"
                  onClick={() => setSelected(null)}
                >
                  <ArrowLeft size={18} />
                </button>
                <div className="chat-person">
                  <div className="seller-avatar">
                    {conversation?.other_name.slice(0, 2).toUpperCase() || 'ML'}
                  </div>
                  <div>
                    <strong>{conversation?.other_name || 'Your conversation'}</strong>
                    <span>{conversation?.listing_title}</span>
                  </div>
                </div>
                <button
                  className="icon-button"
                  aria-label="Report this user"
                  title="Report this conversation"
                  onClick={() => setReporting(true)}
                >
                  <Flag size={17} />
                </button>
                <button
                  className="icon-button"
                  aria-label="Block this user"
                  title="Block this member"
                  onClick={() => void block()}
                >
                  <UserX size={18} />
                </button>
              </header>
              {reporting && conversation && auth.user && (
                <Modal title="Report this conversation" close={() => setReporting(false)}>
                  <form
                    className="form-stack"
                    onSubmit={(event) => {
                      event.preventDefault();
                      const other =
                        conversation.buyer_id === auth.user!.id
                          ? conversation.seller_id
                          : conversation.buyer_id;
                      void request(
                        '/moderation/reports',
                        mutation({
                          target_type: 'user',
                          target_id: other,
                          reason: `${reportReason} (conversation ${conversation.id})`,
                        }),
                      )
                        .then(() => {
                          setReporting(false);
                          setError('Report submitted for review.');
                        })
                        .catch((problem: Error) => setError(problem.message));
                    }}
                  >
                    <label>
                      What happened?
                      <textarea
                        value={reportReason}
                        onChange={(event) => setReportReason(event.target.value)}
                        minLength={5}
                        maxLength={850}
                        required
                      />
                    </label>
                    <button className="button dark">Submit report</button>
                  </form>
                </Modal>
              )}
              <div className="chat-safety">
                <ShieldCheck size={16} />
                Keep it local. Meet in public. Never send a deposit.
              </div>
              <div className="message-list" aria-live="polite">
                {messages.hasNextPage && (
                  <button
                    className="text-button"
                    disabled={messages.isFetchingNextPage}
                    onClick={() => void messages.fetchNextPage()}
                  >
                    {messages.isFetchingNextPage ? 'Loading…' : 'Load older messages'}
                  </button>
                )}
                {messages.isPending && <p className="muted">Loading messages…</p>}
                {messageItems.map((item) => (
                  <div
                    key={item.id}
                    className={`message ${item.sender_id === auth.user?.id ? 'mine' : ''} ${item.message_type === 'viewing' ? 'structured-message' : ''}`}
                  >
                    <p>{item.body}</p>
                    <span>
                      {new Date(item.created_at).toLocaleTimeString('en-IE', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                      {item.sender_id === auth.user?.id && item.read_at ? ' · Read' : ''}
                    </span>
                    {item.warnings.map((warning) => (
                      <div key={warning} className="scam-warning">
                        <ShieldCheck size={14} />
                        {warning}
                      </div>
                    ))}
                  </div>
                ))}
                {viewings.data?.pages
                  .flatMap((page) => page.items)
                  .map((item) => (
                    <div key={item.id} className={`viewing-card status-${item.status}`}>
                      <div className="viewing-label">
                        <CalendarDays size={17} />
                        VIEWING · {item.status.toUpperCase()}
                      </div>
                      <strong>
                        {new Date(item.starts_at).toLocaleString('en-IE', {
                          dateStyle: 'medium',
                          timeStyle: 'short',
                        })}
                      </strong>
                      <p>{item.place}</p>
                      {item.history.length > 0 && (
                        <span className="tiny muted">
                          Revised proposal · version {item.revision}
                        </span>
                      )}
                      <div className="viewing-actions">
                        {item.status === 'proposed' && item.proposed_by !== auth.user?.id && (
                          <>
                            <button
                              className="button primary small"
                              onClick={() => void respond(item, 'accept')}
                            >
                              Accept
                            </button>
                            <button
                              className="button small"
                              onClick={() => {
                                setCounter(item);
                                setProposal(true);
                              }}
                            >
                              Counter
                            </button>
                            <button
                              className="text-button"
                              onClick={() => void respond(item, 'decline')}
                            >
                              Decline
                            </button>
                          </>
                        )}
                        {item.status === 'accepted' && (
                          <button
                            className="button small"
                            onClick={() =>
                              void downloadCalendar(item.id).catch((problem: Error) =>
                                setError(problem.message),
                              )
                            }
                          >
                            <Download size={14} />
                            Calendar
                          </button>
                        )}
                        {['proposed', 'accepted'].includes(item.status) && (
                          <button
                            className="text-button"
                            onClick={() => void respond(item, 'cancel')}
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                {viewings.hasNextPage && (
                  <button
                    className="text-button"
                    disabled={viewings.isFetchingNextPage}
                    onClick={() => void viewings.fetchNextPage()}
                  >
                    {viewings.isFetchingNextPage ? 'Loading…' : 'More viewings'}
                  </button>
                )}
                {viewings.error && (
                  <p className="error" role="alert">
                    {viewings.error.message}
                  </p>
                )}
              </div>
              {proposal && (
                <form className="proposal-form" onSubmit={(event) => void propose(event)}>
                  <strong>{counter ? 'Suggest another time' : 'Arrange a safe viewing'}</strong>
                  <p>
                    Choose a busy public place in daylight. Let someone know where you’re going.
                  </p>
                  <label>
                    Date & time (your local timezone)
                    <input name="time" type="datetime-local" required />
                  </label>
                  <label>
                    Public meeting place
                    <input
                      name="place"
                      minLength={5}
                      maxLength={300}
                      placeholder="e.g. Dundrum shopping centre, main entrance"
                      required
                    />
                  </label>
                  <div className="viewing-actions">
                    <button className="button primary small" disabled={proposing || !online}>
                      {proposing ? 'Sending…' : 'Send proposal'}
                    </button>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => {
                        setProposal(false);
                        setCounter(null);
                      }}
                    >
                      Close
                    </button>
                  </div>
                </form>
              )}
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              {messages.error && <p className="error">{messages.error.message}</p>}
              {draftWarning && (
                <p className="notice" role="status">
                  This browser couldn’t save your draft. Keep this page open until you send it.
                </p>
              )}
              <form className="message-composer" onSubmit={(event) => void send(event)}>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Propose a viewing"
                  onClick={() => setProposal(!proposal)}
                >
                  <CalendarDays size={21} />
                </button>
                <input
                  aria-label="Your message"
                  placeholder="Ask about the listing…"
                  value={body}
                  onChange={(event) => {
                    const value = event.target.value;
                    if (selected) setDrafts((current) => ({ ...current, [selected]: value }));
                  }}
                  maxLength={4000}
                />
                <button
                  className="send-button"
                  aria-label="Send message"
                  disabled={sending || !body.trim() || !online}
                >
                  <Send size={18} />
                </button>
              </form>
            </>
          )}
        </section>
      </div>
    </>
  );
}
