import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { requirePageSession } from "@/server/auth";
import { getAuthorizedArtifact } from "@/server/data";
import { getDatabase } from "@/server/db";
import { verifyMarkdownChecksum } from "@/server/artifacts/store";

export const metadata: Metadata = { title: "Artifact" };

export default async function ArtifactPage({
  params
}: {
  params: Promise<{ artifactId: string }>;
}) {
  const { artifactId } = await params;
  const db = await getDatabase();
  const { user } = await requirePageSession(db);
  const artifact = await getAuthorizedArtifact(db, user.id, artifactId);
  if (!artifact) notFound();

  const integrityVerified = Boolean(
    artifact.content &&
    artifact.checksum &&
    verifyMarkdownChecksum(artifact.content, artifact.checksum)
  );

  return (
    <div className="page artifact-page">
      <header className="page-header">
        <div>
          <Link className="section-label breadcrumb" href={`/app/w/${artifact.workspace.slug}`}>
            {artifact.workspace.name} / Artifact
          </Link>
          <h1>{artifact.title}</h1>
          <p>Durable {artifact.type} output with version, provenance, and integrity metadata.</p>
        </div>
        <span className={`status ${integrityVerified ? "status-ready" : "status-failed"}`}>
          {integrityVerified ? "Integrity verified" : "Integrity issue"}
        </span>
      </header>

      <dl className="artifact-metadata">
        <div>
          <dt>Version</dt>
          <dd>v{artifact.currentVersion}</dd>
        </div>
        <div>
          <dt>Approval</dt>
          <dd>{artifact.approvalState}</dd>
        </div>
        <div>
          <dt>Artifact ID</dt>
          <dd className="metadata">{artifact.id}</dd>
        </div>
        <div>
          <dt>SHA-256</dt>
          <dd className="metadata">{artifact.checksum?.slice(0, 16)}…</dd>
        </div>
      </dl>

      <section className="artifact-document" aria-label="Markdown artifact content">
        <pre>{artifact.content}</pre>
      </section>

      <footer className="artifact-footer">
        {artifact.conversationId && (
          <Link className="button button-secondary" href={`/app/c/${artifact.conversationId}`}>
            Open originating conversation
          </Link>
        )}
        <Link className="button button-quiet" href="/app/ready">
          Return to Ready Dock
        </Link>
      </footer>
    </div>
  );
}
