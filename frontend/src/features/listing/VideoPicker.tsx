import { useEffect, useState } from 'react';
import { Camera, UploadCloud } from 'lucide-react';
import { durationIssue } from './videoValidation';

export function VideoPicker({
  file,
  busy,
  choose,
  validate,
}: {
  file: File | null;
  busy: boolean;
  choose: (file: File | null) => void;
  validate: (issue: string) => void;
}) {
  const [preview, setPreview] = useState('');
  const [unsupported, setUnsupported] = useState(false);
  useEffect(() => {
    setUnsupported(false);
    if (!file) {
      setPreview('');
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  return (
    <div className="video-picker">
      <label className="upload-drop">
        <UploadCloud size={30} />
        <strong>{file?.name || 'Choose your listing video'}</strong>
        <span>15–60 seconds · MP4 or MOV · up to 500 MB</span>
        <input
          aria-label="Listing video"
          type="file"
          accept="video/mp4,video/quicktime,.mp4,.mov"
          required={!file}
          disabled={busy}
          onChange={(event) => choose(event.target.files?.[0] || null)}
        />
      </label>
      <label className="button record-video">
        <Camera size={17} />
        Record a video
        <input
          aria-label="Record listing video"
          className="visually-hidden"
          type="file"
          accept="video/mp4,video/quicktime"
          capture="environment"
          disabled={busy}
          onChange={(event) => choose(event.target.files?.[0] || null)}
        />
      </label>
      {file && preview && (
        <div className="upload-preview">
          <video
            key={preview}
            src={preview}
            controls
            playsInline
            preload="metadata"
            onLoadedMetadata={(event) => validate(durationIssue(event.currentTarget.duration))}
            onError={() => setUnsupported(true)}
          />
          <span className="tiny muted">
            Preview stays on this device until you upload.{' '}
            {Math.round((file.size / 1024 / 1024) * 10) / 10} MB.
          </span>
          {unsupported && (
            <p className="tiny muted">
              This browser can’t preview the recording. You can still upload the original for
              processing.
            </p>
          )}
        </div>
      )}
      {!file && (
        <div className="walkaround-tips">
          <strong>One take. A proper first look.</strong>
          <p>
            Show what you’re selling, highlight its condition and mention anything buyers should
            know. A steady 20–40 second clip is a great start.
          </p>
        </div>
      )}
    </div>
  );
}
