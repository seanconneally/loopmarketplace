import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { mutation, request } from '../../api/client';

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
  const query = useQuery({
    queryKey: ['reports'],
    queryFn: () => request<{ items: Report[] }>('/moderation/queue'),
  });
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">MODERATOR WORKSPACE</div>
          <h1>The review queue.</h1>
          <p>Every decision needs a clear reason.</p>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {query.error && <p className="error">{query.error.message}</p>}
      <div className="review-list">
        {query.data?.items.map((report) => (
          <form
            className="review-card form-stack"
            key={report.id}
            onSubmit={(event) => {
              event.preventDefault();
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
                .catch((problem: Error) => setError(problem.message));
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
                  <select name="action">
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
                  <textarea name="reason" minLength={5} maxLength={1000} required />
                </label>
                <button className="button dark">Record decision</button>
              </>
            )}
          </form>
        ))}
      </div>
      {query.data?.items.length === 0 && (
        <div className="empty-card">
          <h2>All clear for now.</h2>
          <p>No open reports.</p>
        </div>
      )}
    </>
  );
}
