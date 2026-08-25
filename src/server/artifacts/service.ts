import { and, asc, eq } from "drizzle-orm";

import { writeAuditEvent } from "../audit/write";
import { getDatabase } from "../db/client";
import {
  artifactVersions,
  artifacts,
  jobArtifacts,
  type Artifact,
  type ArtifactApprovalState,
  type ArtifactVersion
} from "../db/schema";
import { prepareMarkdownVersion, verifyMarkdownChecksum, type ArtifactProvenance } from "./store";

export interface CreateMarkdownArtifactInput {
  readonly workspaceId: string;
  readonly conversationId?: string | null;
  readonly sourceJobId?: string | null;
  readonly createdByUserId: string;
  readonly title: string;
  readonly markdown: string;
  readonly provenance: ArtifactProvenance;
  readonly approvalState?: ArtifactApprovalState;
  readonly requestId?: string | null;
}

export interface AddMarkdownVersionInput {
  readonly artifactId: string;
  readonly workspaceId: string;
  readonly createdByUserId: string;
  readonly markdown: string;
  readonly provenance: ArtifactProvenance;
  readonly approvalState?: ArtifactApprovalState;
  readonly requestId?: string | null;
}

export interface MarkdownArtifactRecord {
  readonly artifact: Artifact;
  readonly version: ArtifactVersion;
}

export async function createMarkdownArtifact(
  input: CreateMarkdownArtifactInput
): Promise<MarkdownArtifactRecord> {
  const title = input.title.trim();

  if (!title) {
    throw new Error("An artifact title is required.");
  }

  const preparedVersion = prepareMarkdownVersion(input.markdown, input.provenance);
  const db = await getDatabase();
  const created = await db.transaction(async (transaction) => {
    const [artifact] = await transaction
      .insert(artifacts)
      .values({
        workspaceId: input.workspaceId,
        conversationId: input.conversationId ?? null,
        sourceJobId: input.sourceJobId ?? null,
        createdByUserId: input.createdByUserId,
        title,
        kind: "markdown",
        currentVersion: 1,
        approvalState: input.approvalState ?? "draft"
      })
      .returning();

    if (!artifact) {
      throw new Error("The artifact was not persisted.");
    }

    const [version] = await transaction
      .insert(artifactVersions)
      .values({
        artifactId: artifact.id,
        workspaceId: artifact.workspaceId,
        version: 1,
        contentText: preparedVersion.contentText,
        storageProvider: preparedVersion.storageProvider,
        storageKey: preparedVersion.storageKey,
        mimeType: preparedVersion.mimeType,
        byteSize: preparedVersion.byteSize,
        checksumSha256: preparedVersion.checksumSha256,
        provenance: { ...preparedVersion.provenance },
        createdByUserId: input.createdByUserId
      })
      .returning();

    if (!version) {
      throw new Error("The artifact version was not persisted.");
    }

    if (input.sourceJobId) {
      await transaction.insert(jobArtifacts).values({
        jobId: input.sourceJobId,
        artifactId: artifact.id,
        workspaceId: input.workspaceId,
        relation: "output"
      });
    }

    return { artifact, version };
  });

  await writeAuditEvent({
    actorUserId: input.createdByUserId,
    workspaceId: input.workspaceId,
    eventType: "artifact.created",
    targetType: "artifact",
    targetId: created.artifact.id,
    requestId: input.requestId,
    metadata: {
      kind: "markdown",
      version: 1,
      checksumSha256: created.version.checksumSha256
    }
  });

  return created;
}

export async function addMarkdownArtifactVersion(
  input: AddMarkdownVersionInput
): Promise<MarkdownArtifactRecord> {
  const preparedVersion = prepareMarkdownVersion(input.markdown, input.provenance);
  const db = await getDatabase();
  const updated = await db.transaction(async (transaction) => {
    const [currentArtifact] = await transaction
      .select()
      .from(artifacts)
      .where(
        and(
          eq(artifacts.id, input.artifactId),
          eq(artifacts.workspaceId, input.workspaceId),
          eq(artifacts.kind, "markdown")
        )
      )
      .limit(1);

    if (!currentArtifact) {
      throw new Error("The Markdown artifact is unavailable.");
    }

    const nextVersion = currentArtifact.currentVersion + 1;
    const [version] = await transaction
      .insert(artifactVersions)
      .values({
        artifactId: currentArtifact.id,
        workspaceId: currentArtifact.workspaceId,
        version: nextVersion,
        contentText: preparedVersion.contentText,
        storageProvider: preparedVersion.storageProvider,
        storageKey: preparedVersion.storageKey,
        mimeType: preparedVersion.mimeType,
        byteSize: preparedVersion.byteSize,
        checksumSha256: preparedVersion.checksumSha256,
        provenance: { ...preparedVersion.provenance },
        createdByUserId: input.createdByUserId
      })
      .returning();

    if (!version) {
      throw new Error("The artifact version was not persisted.");
    }

    const [artifact] = await transaction
      .update(artifacts)
      .set({
        currentVersion: nextVersion,
        approvalState: input.approvalState ?? currentArtifact.approvalState,
        updatedAt: new Date()
      })
      .where(
        and(
          eq(artifacts.id, currentArtifact.id),
          eq(artifacts.workspaceId, currentArtifact.workspaceId),
          eq(artifacts.currentVersion, currentArtifact.currentVersion)
        )
      )
      .returning();

    if (!artifact) {
      throw new Error("The artifact changed concurrently; reload it before retrying.");
    }

    return { artifact, version };
  });

  await writeAuditEvent({
    actorUserId: input.createdByUserId,
    workspaceId: input.workspaceId,
    eventType: "artifact.version_created",
    targetType: "artifact",
    targetId: input.artifactId,
    requestId: input.requestId,
    metadata: {
      version: updated.version.version,
      checksumSha256: updated.version.checksumSha256
    }
  });

  return updated;
}

export async function getMarkdownArtifact(
  workspaceId: string,
  artifactId: string,
  versionNumber?: number
): Promise<MarkdownArtifactRecord | null> {
  const db = await getDatabase();
  const [artifact] = await db
    .select()
    .from(artifacts)
    .where(
      and(
        eq(artifacts.id, artifactId),
        eq(artifacts.workspaceId, workspaceId),
        eq(artifacts.kind, "markdown")
      )
    )
    .limit(1);

  if (!artifact) {
    return null;
  }

  const selectedVersion = versionNumber ?? artifact.currentVersion;
  const [version] = await db
    .select()
    .from(artifactVersions)
    .where(
      and(
        eq(artifactVersions.artifactId, artifact.id),
        eq(artifactVersions.workspaceId, workspaceId),
        eq(artifactVersions.version, selectedVersion)
      )
    )
    .limit(1);

  if (!version?.contentText) {
    throw new Error("The database-backed Markdown version is unavailable.");
  }

  if (!verifyMarkdownChecksum(version.contentText, version.checksumSha256)) {
    throw new Error("The Markdown artifact checksum verification failed.");
  }

  return { artifact, version };
}

export async function listMarkdownArtifactVersions(
  workspaceId: string,
  artifactId: string
): Promise<ArtifactVersion[]> {
  const db = await getDatabase();
  return db
    .select()
    .from(artifactVersions)
    .where(
      and(
        eq(artifactVersions.workspaceId, workspaceId),
        eq(artifactVersions.artifactId, artifactId)
      )
    )
    .orderBy(asc(artifactVersions.version));
}
