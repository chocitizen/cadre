import { createHash } from "node:crypto";

export const DATABASE_ARTIFACT_STORAGE_PROVIDER = "postgres";
export const MARKDOWN_MIME_TYPE = "text/markdown; charset=utf-8";

export type JsonPrimitive = boolean | number | string | null;
export type JsonValue =
  JsonPrimitive | readonly JsonValue[] | { readonly [key: string]: JsonValue };

export interface ArtifactProvenance {
  readonly source: "conversation" | "job" | "manual" | "import";
  readonly sourceId?: string;
  readonly providerId?: string;
  readonly model?: string;
  readonly promptVersion?: string;
  readonly canonicalStatus?: "working" | "approved" | "canonical" | "archived";
  readonly metadata?: { readonly [key: string]: JsonValue };
}

export interface PreparedMarkdownVersion {
  readonly contentText: string;
  readonly storageProvider: typeof DATABASE_ARTIFACT_STORAGE_PROVIDER;
  readonly storageKey: null;
  readonly mimeType: typeof MARKDOWN_MIME_TYPE;
  readonly byteSize: number;
  readonly checksumSha256: string;
  readonly provenance: ArtifactProvenance;
}

export function prepareMarkdownVersion(
  contentText: string,
  provenance: ArtifactProvenance
): PreparedMarkdownVersion {
  if (!contentText.trim()) {
    throw new Error("Markdown artifact content cannot be empty.");
  }

  const contentBytes = Buffer.from(contentText, "utf8");

  return {
    contentText,
    storageProvider: DATABASE_ARTIFACT_STORAGE_PROVIDER,
    storageKey: null,
    mimeType: MARKDOWN_MIME_TYPE,
    byteSize: contentBytes.byteLength,
    checksumSha256: createHash("sha256").update(contentBytes).digest("hex"),
    provenance
  };
}

export function verifyMarkdownChecksum(
  contentText: string,
  expectedChecksumSha256: string
): boolean {
  const actualChecksum = createHash("sha256")
    .update(Buffer.from(contentText, "utf8"))
    .digest("hex");

  return actualChecksum === expectedChecksumSha256;
}
