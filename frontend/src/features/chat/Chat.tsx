import { useEffect, useState, type FormEvent } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  CalendarDays,
  Download,
  Flag,
  MessageCircle,
  Send,
  ShieldCheck,
  UserX,
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

export function Chat({ initialConversation }: { initialConversation?: string | null }) {
  const auth = useAuth();
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<string | null>(initialConversation || null);
  const [body, setBody] = useState('');
  const [proposal, setProposal] = useState(false);
  const [counter, setCounter] = useState<Viewing | null>(null);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [reportReason, setReportReason] = useState('');
  const conversations = useQuery({
    queryKey: ['conversations', auth.user?.id],
    queryFn: () => request<{ items: Conversation[] }>('/conversations'),
    enabled: !!auth.user,
  });
  const conversation = conversations.data?.items.find((item) => item.id === selected);
  const messages = useQuery({
    queryKey: ['messages', selected],
    queryFn: () =>
      request<{ items: Message[]; next_cursor: string | null }>(
        `/conversations/${selected}/messages`,
      ),
    enabled: !!selected,
    refetchInterval: 10000,
  });
  const viewings = useQuery({
    queryKey: ['viewings', selected],
    queryFn: () => request<{ items: Viewing[] }>(`/viewings?conversation_id=${selected}`),
    enabled: !!selected,
    refetchInterval: 10000,
  });
  useEffect(() => {
    if (initialConversation) setSelected(initialConversation);
  }, [initialConversation]);
  useEffect(() => {
    const last = messages.data?.items.at(-1);
    if (last && !last.read_at && last.sender_id !== auth.user?.id)
      void request(`/conversations/${selected}/read`, {
        method: 'PUT',
        body: JSON.stringify({ message_id: last.id }),
      }).catch(() => undefined);
  }, [messages.data, auth.user?.id, selected]);

  async function send(event: FormEvent) {
    event.preventDefault();
    if (!body.trim() || !selected || sending) return;
    setSending(true);
    setError('');
    try {
      await request(`/conversations/${selected}/messages`, mutation({ body }));
      setBody('');
      await queryClient.invalidateQueries({ queryKey: ['messages', selected] });
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
    const values = new FormData(event.currentTarget);
    try {
      const details = {
        starts_at: new Date(String(values.get('time'))).toISOString(),
        place: String(values.get('place')),
      };
      if (counter)
        await request(
          `/viewings/${counter.id}/respond`,
          mutation({ ...details, action: 'counter', revision: counter.revision }),
        );
      else await request('/viewings', mutation({ ...details, conversation_id: selected }));
      setProposal(false);
      setCounter(null);
      await queryClient.invalidateQueries({ queryKey: ['viewings', selected] });
      await queryClient.invalidateQueries({ queryKey: ['messages', selected] });
    } catch (problem) {
      setError((problem as Error).message);
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
      <div className="page-heading">
        <div>
          <div className="eyebrow">GOOD CONVERSATIONS. GREAT POSSIBILITIES.</div>
          <h1>Your inbox.</h1>
          <p>Ask a question. Arrange a viewing. Meet your next car.</p>
        </div>
      </div>
      <div className="chat-layout">
        <aside className="conversation-list">
          <div className="panel-kicker">CONVERSATIONS</div>
          {conversations.isPending && <p className="muted">Loading conversations…</p>}
          {conversations.error && <p className="error">{conversations.error.message}</p>}
          {conversations.data?.items.map((item) => (
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
          {conversations.data?.items.length === 0 && (
            <p className="muted">Find a car you like and message its seller to get started.</p>
          )}
        </aside>
        <section className="chat-panel">
          {!selected ? (
            <div className="chat-placeholder">
              <MessageCircle size={42} />
              <h2>A good place to start.</h2>
              <p>Select a conversation to see what’s next.</p>
            </div>
          ) : (
            <>
              <header className="chat-header">
                <div>
                  <strong>{conversation?.other_name || 'Your conversation'}</strong>
                  <span>{conversation?.listing_title}</span>
                </div>
                <button
                  className="icon-button"
                  aria-label="Report this user"
                  onClick={() => setReporting(true)}
                >
                  <Flag size={17} />
                </button>
                <button
                  className="icon-button"
                  aria-label="Block this user"
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
                {messages.data?.next_cursor && (
                  <p className="tiny muted">
                    Showing the latest 50 messages. Older history is available through the API.
                  </p>
                )}
                {messages.data?.items.map((item) => (
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
                {viewings.data?.items.map((item) => (
                  <div key={item.id} className="viewing-card">
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
                      <span className="tiny muted">Revised proposal · version {item.revision}</span>
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
                    <button className="button primary small">Send proposal</button>
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
                  placeholder="Ask about the car…"
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                  maxLength={4000}
                />
                <button
                  className="send-button"
                  aria-label="Send message"
                  disabled={sending || !body.trim()}
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
