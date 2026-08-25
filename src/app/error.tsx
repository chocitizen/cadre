"use client";

export default function GlobalError({
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="offline-page" id="main-content">
      <span className="brand-glyph" aria-hidden="true">
        C
      </span>
      <div>
        <p className="section-label">Execution interrupted</p>
        <h1>CADRE could not complete this view.</h1>
        <p>The failure was contained. Retry the request or return to command overview.</p>
        <div className="page-actions">
          <button className="button button-primary" onClick={reset} type="button">
            Retry
          </button>
          <a className="button button-secondary" href="/app">
            Return to overview
          </a>
        </div>
      </div>
    </main>
  );
}
