import {
  ObsidianIntegrationDisabledError,
  type ObsidianAdapter,
  type ObsidianAdapterStatus,
  type ObsidianDocument,
  type ObsidianDocumentReference
} from "./contract";

const DISABLED_STATUS: ObsidianAdapterStatus = {
  enabled: false,
  mode: "disabled",
  reason:
    "Obsidian remains a separate canonical document repository; synchronization is deferred pending explicit authority and conflict rules."
};

export class DisabledObsidianAdapter implements ObsidianAdapter {
  async status(): Promise<ObsidianAdapterStatus> {
    return DISABLED_STATUS;
  }

  async readDocument(reference: ObsidianDocumentReference): Promise<ObsidianDocument> {
    void reference;
    throw new ObsidianIntegrationDisabledError();
  }
}

export const disabledObsidianAdapter = new DisabledObsidianAdapter();
