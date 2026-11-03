export function selectionIssue(file: Pick<File, 'name' | 'size' | 'type'>): string {
  if (!file.size) return 'This video is empty. Choose your original recording.';
  if (file.size > 500 * 1024 * 1024) return 'Choose a video up to 500 MB.';
  if (!/\.(mp4|mov)$/i.test(file.name) && !['video/mp4', 'video/quicktime'].includes(file.type))
    return 'Choose an MP4 or MOV video.';
  return '';
}

export function durationIssue(duration: number): string {
  if (!Number.isFinite(duration) || duration <= 0) return '';
  return duration < 15
    ? 'Keep your walkaround between 15 and 60 seconds. This one is too short.'
    : duration > 60
      ? 'This video is longer than 60 seconds. Trim it before uploading.'
      : '';
}
