import { Component, type ReactNode } from 'react';
import { RefreshCw } from 'lucide-react';
import { BrandMark } from './Brand';

export class ErrorBoundary extends Component<
  { children: ReactNode; resetKey?: string; onReset?: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidUpdate(previous: Readonly<{ resetKey?: string }>) {
    if (this.state.failed && previous.resetKey !== this.props.resetKey)
      this.setState({ failed: false });
  }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <section className="recovery-screen" role="alert" aria-labelledby="recovery-title">
        <BrandMark />
        <span className="eyebrow">LET’S GET YOU MOVING AGAIN</span>
        <h1 id="recovery-title">Something went wrong on this page.</h1>
        <p>Try opening it again. Saved adverts and uploads are still available in My cars.</p>
        <div className="recovery-actions">
          <button
            className="button dark"
            onClick={() => {
              this.props.onReset?.();
              this.setState({ failed: false });
            }}
          >
            <RefreshCw size={17} /> Try again
          </button>
          <button className="button" onClick={() => window.location.reload()}>
            Reload Motorloop
          </button>
          <a href="/" className="text-button">
            Back to discover
          </a>
        </div>
      </section>
    );
  }
}
