import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { mutation, request } from '../../api/client';
import { ShieldCheck } from 'lucide-react';
import { PageHeading } from '../../shared/PageHeading';

type Report = {
  id: string;
  target_type: string;
  target_id: string;
  reason: string;
  status: string;
};
export function Moderation() {
  const queryClient = useQueryClient();
  const [error, setError] = useState('');
  const [recording, setRecording] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ['reports'],
    queryFn: () => request<{ items: Report[] }>('/moderation/queue'),
  });
  return (
    <>
      <PageHeading
        eyebrow="THE MODERATOR WORKSPACE"
        title={
          <>
            A fair review. <span>A clear decision.</span>
          </>
        }
        description="Review flagged activity and record the reason behind every decision."
        action={
          <span className="section-pill">
            <ShieldCheck size={16} />
            Decisions are recorded
          </span>
        }
      />
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {query.error && <p className="error">{query.error.message}</p>}
      <div className="review-list">
        {query.data?.items.map((report) => (
          <form
            className="review-card form-stack"
            key={report.id}
            onSubmit={(event) => {
              event.preventDefault();
              if (recording) return;
              setRecording(report.id);
              setError('');
              const data = new FormData(event.currentTarget);
              void request(
                '/moderation/actions',
                mutation({
                  target_type: report.target_type,
                  target_id: report.target_id,
                  action: data.get('action'),
                  reason: data.get('reason'),
                }),
              )
                .then(() => queryClient.invalidateQueries({ queryKey: ['reports'] }))
                .catch((problem: Error) => setError(problem.message))
                .finally(() => setRecording(null));
            }}
          >
            <div className="eyebrow">
              {report.target_type} · {report.status}
            </div>
            <strong>{report.reason}</strong>
            <code>{report.target_id}</code>
            {report.target_type === 'message' ? (
              <p className="muted">
                Message review requires the full evidence viewer before public launch. Review
                through an authorized operator workflow.
              </p>
            ) : (
              <>
                <label>
                  Decision
                  <select name="action" disabled={recording === report.id}>
                    {report.target_type === 'listing' ? (
                      <>
                        <option value="approve">Approve</option>
                        <option value="remove">Remove</option>
                      </>
                    ) : (
                      <option value="suspend">Suspend user</option>
                    )}
                  </select>
                </label>
                <label>
                  Statement of reasons
                  <textarea
                    name="reason"
                    minLength={5}
                    maxLength={1000}
                    required
                    placeholder="Explain the decision clearly. This becomes part of the review record."
                    disabled={recording === report.id}
                  />
                </label>
                <button className="button dark" disabled={!!recording}>
                  {recording === report.id ? 'Recording decision…' : 'Record decision'}
                </button>
              </>
            )}
          </form>
        ))}
      </div>
      {query.data?.items.length === 0 && (
        <div className="empty-card">
          <ShieldCheck size={36} />
          <h2>All clear for now.</h2>
          <p>There are no open reports waiting for review.</p>
        </div>
      )}
    </>
  );
}
