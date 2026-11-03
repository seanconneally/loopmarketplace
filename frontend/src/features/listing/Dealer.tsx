import { useState, type FormEvent } from 'react';
import { UploadCloud } from 'lucide-react';
import { mutation, request } from '../../api/client';
import { uploadVideo } from './uploads';

type ImportJob = {
  id: string;
  status: string;
  rows: { row: number; listing_id?: string; video_filename?: string; error?: string }[];
};
export function Dealer() {
  const [csv, setCsv] = useState<File | null>(null);
  const [videos, setVideos] = useState<File[]>([]);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<string[]>([]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!csv) return;
    setBusy(true);
    setResults([]);
    try {
      let job = await request<ImportJob>(
        '/dealer/imports',
        mutation({ csv_text: await csv.text(), rights_confirmed: true }),
      );
      setStatus('Validating your inventory…');
      for (let attempt = 0; attempt < 120 && job.status !== 'completed'; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        job = await request<ImportJob>(`/dealer/imports/${job.id}`);
      }
      if (job.status !== 'completed')
        throw new Error(`Import ${job.id} is queued. Poll its API status to resume later.`);
      for (const row of job.rows) {
        if (row.error) {
          setResults((previous) => [...previous, `Row ${row.row}: ${row.error}`]);
          continue;
        }
        const file = videos.find((video) => video.name === row.video_filename);
        if (!file || !row.listing_id) {
          setResults((previous) => [
            ...previous,
            `Row ${row.row}: draft ${row.listing_id}; matching video file was not selected.`,
          ]);
          continue;
        }
        const state = await uploadVideo(row.listing_id, file, (message) =>
          setStatus(`Row ${row.row}: ${message}`),
        );
        setResults((previous) => [...previous, `Row ${row.row}: ${state}`]);
      }
      setStatus('Import complete. Each video follows the usual safety checks.');
    } catch (problem) {
      setStatus((problem as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">VERIFIED DEALER STUDIO</div>
          <h1>Bring your forecourt online.</h1>
          <p>One CSV. Your own videos. A whole new audience.</p>
        </div>
      </div>
      <form className="form-stack review-card" onSubmit={(event) => void submit(event)}>
        <UploadCloud size={32} />
        <p className="muted">
          Start with the sample in docs/dealer-template.csv. Price is in integer euro cents. Match
          each video_filename to a selected file. Maximum 100 rows per import.
        </p>
        <label>
          Inventory CSV
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(event) => setCsv(event.target.files?.[0] || null)}
            required
          />
        </label>
        <label>
          Matching videos
          <input
            type="file"
            multiple
            accept="video/mp4,video/quicktime,.mov"
            onChange={(event) => setVideos(Array.from(event.target.files || []))}
          />
        </label>
        <label className="checkbox">
          <input type="checkbox" required />I own or am authorized to advertise every vehicle and
          video in this import.
        </label>
        <button className="button primary" disabled={busy}>
          {busy ? 'Importing inventory…' : 'Import inventory'}
        </button>
        {status && (
          <p className="notice" role="status">
            {status}
          </p>
        )}
        {results.map((result) => (
          <p key={result} className="tiny">
            {result}
          </p>
        ))}
      </form>
    </>
  );
}
