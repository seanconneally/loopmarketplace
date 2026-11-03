import { useState, type FormEvent } from 'react';
import { Download, FileSpreadsheet, UploadCloud } from 'lucide-react';
import { mutation, request } from '../../api/client';
import { uploadVideo } from './uploads';
import { PageHeading } from '../../shared/PageHeading';

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
      <PageHeading
        eyebrow="YOUR DEALER STUDIO"
        title={
          <>
            Your forecourt. <span>A fresh audience.</span>
          </>
        }
        description="Car inventory imports with your own walkaround videos. Use Sell something for other listings."
        action={
          <span className="section-pill">
            <FileSpreadsheet size={16} />
            Up to 100 adverts per import
          </span>
        }
      />
      <div className="studio-layout">
        <form className="form-stack studio-panel" onSubmit={(event) => void submit(event)}>
          <div className="form-section-heading">
            <span>01</span>
            <div>
              <strong>Start with your inventory</strong>
              <p>Use the template so every advert has the right details.</p>
            </div>
          </div>
          <label className="upload-drop">
            <FileSpreadsheet size={30} />
            <strong>Inventory CSV</strong>
            <span>{csv?.name || 'Choose your completed inventory file'}</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => setCsv(event.target.files?.[0] || null)}
              required
              disabled={busy}
            />
          </label>
          <div className="form-section-heading">
            <span>02</span>
            <div>
              <strong>Add the walkarounds</strong>
              <p>Video names should match the filenames in your template.</p>
            </div>
          </div>
          <label className="upload-drop">
            <UploadCloud size={30} />
            <strong>Matching videos</strong>
            <span>
              {videos.length
                ? `${videos.length} video${videos.length === 1 ? '' : 's'} selected`
                : 'Select the original MP4 or MOV files'}
            </span>
            <input
              type="file"
              multiple
              accept="video/mp4,video/quicktime,.mov"
              onChange={(event) => setVideos(Array.from(event.target.files || []))}
              disabled={busy}
            />
          </label>
          {videos.length > 0 && (
            <div className="studio-file-summary">
              {videos.slice(0, 4).map((video, index) => (
                <span key={`${video.name}-${index}`}>{video.name}</span>
              ))}
              {videos.length > 4 && <span>+{videos.length - 4} more</span>}
            </div>
          )}
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
        <aside className="studio-guide">
          <h2>
            From inventory
            <br />
            to first impression.
          </h2>
          <div className="studio-steps">
            <div>
              <span>1</span>
              <div>
                <strong>Prepare the template</strong>
                <p>
                  Fill in your cars and their video filenames. Prices use cents: €19,950 is 1995000.
                </p>
              </div>
            </div>
            <div>
              <span>2</span>
              <div>
                <strong>Match your videos</strong>
                <p>A 15–60 second walkaround for each car. Keep the original file names.</p>
              </div>
            </div>
            <div>
              <span>3</span>
              <div>
                <strong>We’ll check the details</strong>
                <p>
                  Each advert follows the normal processing and safety checks. Manage drafts in My
                  listings.
                </p>
              </div>
            </div>
          </div>
          <a className="button" href="/dealer-template.csv" download>
            <Download size={16} />
            Download template
          </a>
        </aside>
      </div>
    </>
  );
}
