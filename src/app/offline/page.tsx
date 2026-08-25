import { BrandMark } from "@/components/brand-mark";

export default function OfflinePage() {
  return (
    <main className="offline-page" id="main-content">
      <BrandMark />
      <div>
        <p className="section-label">Connection unavailable</p>
        <h1>CADRE is offline.</h1>
        <p>Reconnect to open private workspaces, conversations, and artifacts.</p>
        <a href="/app" className="button button-primary">
          Retry connection
        </a>
      </div>
    </main>
  );
}
