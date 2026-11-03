import { afterEach, expect, test, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { VideoPicker } from './VideoPicker';
import { durationIssue, selectionIssue } from './videoValidation';

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test('video selection rejects empty, oversized and unsupported originals before uploading', () => {
  expect(selectionIssue({ name: 'car.mp4', type: 'video/mp4', size: 0 })).toContain('empty');
  expect(selectionIssue({ name: 'car.mp4', type: 'video/mp4', size: 501 * 1024 * 1024 })).toContain(
    '500 MB',
  );
  expect(selectionIssue({ name: 'photo.jpg', type: 'image/jpeg', size: 1000 })).toContain(
    'MP4 or MOV',
  );
  expect(selectionIssue({ name: 'CAR.MOV', type: '', size: 1000 })).toBe('');
});

test('local duration checks catch short/long videos without rejecting unpreviewable codecs', () => {
  expect(durationIssue(14)).toContain('too short');
  expect(durationIssue(61)).toContain('Trim');
  expect(durationIssue(15)).toBe('');
  expect(durationIssue(60)).toBe('');
  expect(durationIssue(Number.NaN)).toBe('');
});

test('preview uses a local object URL, validates metadata and releases the URL', () => {
  const release = vi.fn();
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn(() => 'blob:local-preview'),
    revokeObjectURL: release,
  });
  const validate = vi.fn();
  const { container, unmount } = render(
    <VideoPicker
      file={new File(['video'], 'owned.mp4', { type: 'video/mp4' })}
      busy={false}
      choose={vi.fn()}
      validate={validate}
    />,
  );
  const video = container.querySelector('video')!;
  expect(video.src).toContain('blob:local-preview');
  Object.defineProperty(video, 'duration', { value: 65 });
  fireEvent.loadedMetadata(video);
  expect(validate).toHaveBeenCalledWith(expect.stringContaining('Trim'));
  fireEvent.error(video);
  expect(screen.getByText(/can’t preview/)).toBeInTheDocument();
  unmount();
  expect(release).toHaveBeenCalledWith('blob:local-preview');
});
