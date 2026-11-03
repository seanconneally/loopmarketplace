export function BrandMark({ className = '' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <rect width="40" height="40" rx="13" fill="currentColor" />
      <path
        d="M10 27V17a4 4 0 0 1 8 0v10-7a4 4 0 0 1 8 0v7m-2-15h7v7m0-7-8 8"
        stroke="var(--brand-mark-line, #dff47a)"
        strokeWidth="2.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function LoopArtwork() {
  return (
    <svg className="loop-artwork" viewBox="0 0 240 150" fill="none" aria-hidden="true">
      <path
        d="M-35 123h108c39 0 39-95 78-95h102"
        stroke="currentColor"
        strokeOpacity=".12"
        strokeWidth="64"
      />
      <path
        d="M-35 123h108c39 0 39-95 78-95h102"
        stroke="currentColor"
        strokeOpacity=".5"
        strokeWidth="1.5"
        strokeDasharray="5 7"
      />
      <circle cx="153" cy="28" r="11" fill="currentColor" fillOpacity=".15" />
      <circle cx="153" cy="28" r="4" fill="currentColor" />
      <path
        d="m67 113 9 10-9 10"
        stroke="currentColor"
        strokeOpacity=".65"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
