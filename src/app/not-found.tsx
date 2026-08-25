import { BrandMark } from "@/components/brand-mark";

export default function NotFoundPage() {
  return (
    <main className="offline-page" id="main-content">
      <BrandMark />
      <div>
        <p className="section-label">Not found</p>
        <h1>This record is not available.</h1>
        <p>It may not exist, may have moved, or may be outside your authorized workspace.</p>
        <a className="button button-primary" href="/app">
          Return to overview
        </a>
      </div>
    </main>
  );
}
