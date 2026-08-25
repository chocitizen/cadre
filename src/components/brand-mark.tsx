import Link from "next/link";

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <Link className="brand-mark" href="/app" aria-label="CADRE home">
      <span className="brand-glyph" aria-hidden="true">
        C
      </span>
      {!compact && (
        <span className="brand-word">
          CADRE <small>Command</small>
        </span>
      )}
    </Link>
  );
}
