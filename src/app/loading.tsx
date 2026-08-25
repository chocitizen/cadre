export default function LoadingPage() {
  return (
    <main className="page" id="main-content" aria-busy="true" aria-label="Loading CADRE">
      <div className="page-header">
        <div className="skeleton skeleton-title" />
      </div>
      <div className="surface-section">
        <div className="skeleton skeleton-row" />
        <div className="skeleton skeleton-row" />
        <div className="skeleton skeleton-row" />
      </div>
    </main>
  );
}
