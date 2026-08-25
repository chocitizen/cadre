export type ObsidianAuthority = "obsidian" | "cadre";

export interface ObsidianDocumentReference {
  readonly vaultPath: string;
  readonly relativePath: string;
  readonly checksumSha256: string;
  readonly modifiedAt: Date;
  readonly authority: ObsidianAuthority;
}

export interface ObsidianDocument extends ObsidianDocumentReference {
  readonly markdown: string;
}

export interface ObsidianAdapterStatus {
  readonly enabled: boolean;
  readonly mode: "disabled" | "read_only";
  readonly reason: string;
}

export interface ObsidianAdapter {
  status(): Promise<ObsidianAdapterStatus>;
  readDocument(reference: ObsidianDocumentReference): Promise<ObsidianDocument>;
}

export class ObsidianIntegrationDisabledError extends Error {
  constructor() {
    super(
      "The Obsidian integration is disabled until authority, conflict, and synchronization rules are approved."
    );
    this.name = "ObsidianIntegrationDisabledError";
  }
}
