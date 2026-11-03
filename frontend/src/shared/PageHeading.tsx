import type { ReactNode } from 'react';

export function PageHeading({
  eyebrow,
  title,
  description,
  action,
  className = '',
}: {
  eyebrow: string;
  title: ReactNode;
  description: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`page-heading ${className}`}>
      <div>
        <div className="eyebrow">
          <span className="eyebrow-line" />
          {eyebrow}
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action && <div className="page-heading-action">{action}</div>}
    </div>
  );
}
