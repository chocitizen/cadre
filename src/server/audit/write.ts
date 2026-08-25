import { getDatabase } from "../db/client";
import { AUDIT_OUTCOMES, auditEvents, type AuditEvent } from "../db/schema";

export type AuditOutcome = (typeof AUDIT_OUTCOMES)[number];
export type AuditMetadataValue = boolean | number | string | null;
export type AuditMetadata = Readonly<Record<string, AuditMetadataValue>>;

export interface WriteAuditEventInput {
  readonly actorUserId?: string | null;
  readonly workspaceId?: string | null;
  readonly eventType: string;
  readonly targetType?: string | null;
  readonly targetId?: string | null;
  readonly outcome?: AuditOutcome;
  readonly requestId?: string | null;
  readonly metadata?: AuditMetadata;
}

const SENSITIVE_METADATA_KEY =
  /(authorization|cookie|credential|password|secret|token|api.?key|prompt|message|content|request.?body|response.?body)/i;

export function validateAuditMetadata(
  metadata: AuditMetadata = {}
): Record<string, AuditMetadataValue> {
  const validated: Record<string, AuditMetadataValue> = {};

  for (const [key, value] of Object.entries(metadata)) {
    if (SENSITIVE_METADATA_KEY.test(key)) {
      throw new Error(`Sensitive audit metadata key is not permitted: ${key}`);
    }

    if (typeof value === "string" && value.length > 512) {
      throw new Error(`Audit metadata value is too long: ${key}`);
    }

    validated[key] = value;
  }

  return validated;
}

export async function writeAuditEvent(input: WriteAuditEventInput): Promise<AuditEvent> {
  if (!input.eventType.trim()) {
    throw new Error("An audit event type is required.");
  }

  const db = await getDatabase();
  const [createdEvent] = await db
    .insert(auditEvents)
    .values({
      actorUserId: input.actorUserId ?? null,
      workspaceId: input.workspaceId ?? null,
      eventType: input.eventType.trim(),
      targetType: input.targetType?.trim() || null,
      targetId: input.targetId ?? null,
      outcome: input.outcome ?? "success",
      requestId: input.requestId?.trim() || null,
      metadata: validateAuditMetadata(input.metadata)
    })
    .returning();

  if (!createdEvent) {
    throw new Error("The audit event was not persisted.");
  }

  return createdEvent;
}
