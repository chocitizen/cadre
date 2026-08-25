import { sql } from "drizzle-orm";
import {
  boolean,
  check,
  foreignKey,
  index,
  integer,
  jsonb,
  pgTable,
  pgView,
  primaryKey,
  text,
  timestamp,
  unique,
  uniqueIndex,
  uuid
} from "drizzle-orm/pg-core";

const createdAt = () =>
  timestamp("created_at", { withTimezone: true, mode: "date" }).notNull().defaultNow();
const updatedAt = () =>
  timestamp("updated_at", { withTimezone: true, mode: "date" }).notNull().defaultNow();

export const USER_ROLES = ["owner", "admin", "member"] as const;
export const USER_STATUSES = ["active", "disabled"] as const;
export const WORKSPACE_ROLES = ["owner", "admin", "member", "viewer"] as const;
export const WORKSPACE_STATUSES = ["active", "archived"] as const;
export const CONVERSATION_STATUSES = ["active", "archived"] as const;
export const MESSAGE_ROLES = ["user", "assistant", "system", "tool"] as const;
export const MESSAGE_STATUSES = ["pending", "completed", "failed"] as const;
export const JOB_EXECUTION_MODES = ["inline", "worker"] as const;
export const JOB_STATUSES = [
  "queued",
  "running",
  "needs_approval",
  "review",
  "ready",
  "failed",
  "delivered",
  "archived"
] as const;
export const ARTIFACT_APPROVAL_STATES = [
  "draft",
  "review",
  "approved",
  "rejected",
  "archived"
] as const;
export const NOTIFICATION_STATUSES = ["unread", "read", "archived"] as const;
export const AUDIT_OUTCOMES = ["success", "failure", "denied"] as const;

export type UserRole = (typeof USER_ROLES)[number];
export type WorkspaceRole = (typeof WORKSPACE_ROLES)[number];
export type JobStatus = (typeof JOB_STATUSES)[number];
export type ArtifactApprovalState = (typeof ARTIFACT_APPROVAL_STATES)[number];

export const users = pgTable(
  "users",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    email: text("email").notNull(),
    displayName: text("display_name").notNull(),
    passwordHash: text("password_hash").notNull(),
    role: text("role").$type<UserRole>().notNull().default("member"),
    status: text("status").notNull().default("active"),
    lastLoginAt: timestamp("last_login_at", { withTimezone: true, mode: "date" }),
    createdAt: createdAt(),
    updatedAt: updatedAt()
  },
  (table) => [
    uniqueIndex("users_email_lower_unique").on(sql`lower(${table.email})`),
    check("users_email_normalized_check", sql`${table.email} = lower(btrim(${table.email}))`),
    check("users_role_check", sql`${table.role} in ('owner', 'admin', 'member')`),
    check("users_status_check", sql`${table.status} in ('active', 'disabled')`)
  ]
);

export const sessions = pgTable(
  "sessions",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    tokenHash: text("token_hash").notNull(),
    csrfTokenHash: text("csrf_token_hash").notNull(),
    userAgentHash: text("user_agent_hash"),
    createdAt: createdAt(),
    lastSeenAt: timestamp("last_seen_at", { withTimezone: true, mode: "date" })
      .notNull()
      .defaultNow(),
    idleExpiresAt: timestamp("idle_expires_at", { withTimezone: true, mode: "date" }).notNull(),
    absoluteExpiresAt: timestamp("absolute_expires_at", {
      withTimezone: true,
      mode: "date"
    }).notNull(),
    revokedAt: timestamp("revoked_at", { withTimezone: true, mode: "date" })
  },
  (table) => [
    uniqueIndex("sessions_token_hash_unique").on(table.tokenHash),
    index("sessions_user_active_idx").on(table.userId, table.revokedAt, table.idleExpiresAt),
    check("sessions_expiry_order_check", sql`${table.idleExpiresAt} <= ${table.absoluteExpiresAt}`)
  ]
);

export const authThrottles = pgTable(
  "auth_throttles",
  {
    identifierHash: text("identifier_hash").primaryKey(),
    attemptCount: integer("attempt_count").notNull().default(0),
    windowStartedAt: timestamp("window_started_at", { withTimezone: true, mode: "date" })
      .notNull()
      .defaultNow(),
    blockedUntil: timestamp("blocked_until", { withTimezone: true, mode: "date" }),
    updatedAt: updatedAt()
  },
  (table) => [check("auth_throttles_attempt_count_check", sql`${table.attemptCount} >= 0`)]
);

export const workspaces = pgTable(
  "workspaces",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    slug: text("slug").notNull(),
    name: text("name").notNull(),
    description: text("description"),
    status: text("status").notNull().default("active"),
    createdByUserId: uuid("created_by_user_id").references(() => users.id, {
      onDelete: "set null"
    }),
    createdAt: createdAt(),
    updatedAt: updatedAt()
  },
  (table) => [
    unique("workspaces_slug_unique").on(table.slug),
    check("workspaces_slug_check", sql`${table.slug} ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'`),
    check("workspaces_status_check", sql`${table.status} in ('active', 'archived')`)
  ]
);

export const workspaceMemberships = pgTable(
  "workspace_memberships",
  {
    workspaceId: uuid("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    role: text("role").$type<WorkspaceRole>().notNull().default("member"),
    createdAt: createdAt(),
    updatedAt: updatedAt()
  },
  (table) => [
    primaryKey({ columns: [table.workspaceId, table.userId], name: "workspace_memberships_pk" }),
    index("workspace_memberships_user_idx").on(table.userId),
    check(
      "workspace_memberships_role_check",
      sql`${table.role} in ('owner', 'admin', 'member', 'viewer')`
    )
  ]
);

export const conversations = pgTable(
  "conversations",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    workspaceId: uuid("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
    createdByUserId: uuid("created_by_user_id")
      .notNull()
      .references(() => users.id, { onDelete: "restrict" }),
    title: text("title").notNull().default("Untitled conversation"),
    status: text("status").notNull().default("active"),
    provider: text("provider"),
    model: text("model"),
    lastMessageAt: timestamp("last_message_at", { withTimezone: true, mode: "date" }),
    createdAt: createdAt(),
    updatedAt: updatedAt()
  },
  (table) => [
    unique("conversations_id_workspace_unique").on(table.id, table.workspaceId),
    index("conversations_workspace_recent_idx").on(table.workspaceId, table.lastMessageAt),
    check("conversations_status_check", sql`${table.status} in ('active', 'archived')`)
  ]
);

export const messages = pgTable(
  "messages",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    workspaceId: uuid("workspace_id").notNull(),
    conversationId: uuid("conversation_id").notNull(),
    sequence: integer("sequence").notNull(),
    role: text("role").notNull(),
    contentText: text("content_text").notNull(),
    structuredContent: jsonb("structured_content").$type<Record<string, unknown>>(),
    createdByUserId: uuid("created_by_user_id").references(() => users.id, {
      onDelete: "set null"
    }),
    status: text("status").notNull().default("completed"),
    provider: text("provider"),
    model: text("model"),
    providerResponseId: text("provider_response_id"),
    promptKey: text("prompt_key"),
    promptVersion: integer("prompt_version"),
    inputTokens: integer("input_tokens"),
    outputTokens: integer("output_tokens"),
    retrievalContext: jsonb("retrieval_context").$type<Record<string, unknown>>(),
    clientRequestId: text("client_request_id"),
    createdAt: createdAt(),
    updatedAt: updatedAt()
  },
  (table) => [
    foreignKey({
      columns: [table.conversationId, table.workspaceId],
      foreignColumns: [conversations.id, conversations.workspaceId],
      name: "messages_conversation_workspace_fk"
    }).onDelete("cascade"),
    unique("messages_conversation_sequence_unique").on(table.conversationId, table.sequence),
    unique("messages_conversation_client_request_unique").on(
      table.conversationId,
      table.clientRequestId
    ),
    index("messages_conversation_created_idx").on(table.conversationId, table.createdAt),
    check("messages_sequence_check", sql`${table.sequence} > 0`),
    check("messages_role_check", sql`${table.role} in ('user', 'assistant', 'system', 'tool')`),
    check("messages_status_check", sql`${table.status} in ('pending', 'completed', 'failed')`),
    check(
      "messages_input_tokens_check",
      sql`${table.inputTokens} is null or ${table.inputTokens} >= 0`
    ),
    check(
      "messages_output_tokens_check",
      sql`${table.outputTokens} is null or ${table.outputTokens} >= 0`
    )
  ]
);

export const jobs = pgTable(
  "jobs",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    workspaceId: uuid("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
    conversationId: uuid("conversation_id"),
    requestedByUserId: uuid("requested_by_user_id")
      .notNull()
      .references(() => users.id, { onDelete: "restrict" }),
    operation: text("operation").notNull(),
    executionMode: text("execution_mode").notNull().default("inline"),
    status: text("status").$type<JobStatus>().notNull().default("queued"),
    progress: integer("progress").notNull().default(0),
    inputMetadata: jsonb("input_metadata").$type<Record<string, unknown>>(),
    outputMetadata: jsonb("output_metadata").$type<Record<string, unknown>>(),
    errorCode: text("error_code"),
    errorMessage: text("error_message"),
    idempotencyKey: text("idempotency_key"),
    surfaceInReadyDock: boolean("surface_in_ready_dock").notNull().default(false),
    createdAt: createdAt(),
    startedAt: timestamp("started_at", { withTimezone: true, mode: "date" }),
    completedAt: timestamp("completed_at", { withTimezone: true, mode: "date" }),
    updatedAt: updatedAt()
  },
  (table) => [
    unique("jobs_id_workspace_unique").on(table.id, table.workspaceId),
    unique("jobs_workspace_idempotency_unique").on(table.workspaceId, table.idempotencyKey),
    foreignKey({
      columns: [table.conversationId, table.workspaceId],
      foreignColumns: [conversations.id, conversations.workspaceId],
      name: "jobs_conversation_workspace_fk"
    }).onDelete("restrict"),
    index("jobs_workspace_status_idx").on(table.workspaceId, table.status, table.createdAt),
    check("jobs_execution_mode_check", sql`${table.executionMode} in ('inline', 'worker')`),
    check(
      "jobs_status_check",
      sql`${table.status} in ('queued', 'running', 'needs_approval', 'review', 'ready', 'failed', 'delivered', 'archived')`
    ),
    check("jobs_progress_check", sql`${table.progress} between 0 and 100`)
  ]
);

export const artifacts = pgTable(
  "artifacts",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    workspaceId: uuid("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
    conversationId: uuid("conversation_id"),
    sourceJobId: uuid("source_job_id"),
    createdByUserId: uuid("created_by_user_id")
      .notNull()
      .references(() => users.id, { onDelete: "restrict" }),
    title: text("title").notNull(),
    kind: text("kind").notNull(),
    currentVersion: integer("current_version").notNull().default(1),
    approvalState: text("approval_state").$type<ArtifactApprovalState>().notNull().default("draft"),
    createdAt: createdAt(),
    updatedAt: updatedAt()
  },
  (table) => [
    unique("artifacts_id_workspace_unique").on(table.id, table.workspaceId),
    foreignKey({
      columns: [table.conversationId, table.workspaceId],
      foreignColumns: [conversations.id, conversations.workspaceId],
      name: "artifacts_conversation_workspace_fk"
    }).onDelete("restrict"),
    foreignKey({
      columns: [table.sourceJobId, table.workspaceId],
      foreignColumns: [jobs.id, jobs.workspaceId],
      name: "artifacts_source_job_workspace_fk"
    }).onDelete("restrict"),
    index("artifacts_workspace_updated_idx").on(table.workspaceId, table.updatedAt),
    check("artifacts_current_version_check", sql`${table.currentVersion} > 0`),
    check(
      "artifacts_approval_state_check",
      sql`${table.approvalState} in ('draft', 'review', 'approved', 'rejected', 'archived')`
    )
  ]
);

export const artifactVersions = pgTable(
  "artifact_versions",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    artifactId: uuid("artifact_id").notNull(),
    workspaceId: uuid("workspace_id").notNull(),
    version: integer("version").notNull(),
    contentText: text("content_text"),
    storageProvider: text("storage_provider").notNull().default("postgres"),
    storageKey: text("storage_key"),
    mimeType: text("mime_type").notNull(),
    byteSize: integer("byte_size").notNull(),
    checksumSha256: text("checksum_sha256").notNull(),
    provenance: jsonb("provenance").$type<Record<string, unknown>>().notNull(),
    createdByUserId: uuid("created_by_user_id")
      .notNull()
      .references(() => users.id, { onDelete: "restrict" }),
    createdAt: createdAt()
  },
  (table) => [
    foreignKey({
      columns: [table.artifactId, table.workspaceId],
      foreignColumns: [artifacts.id, artifacts.workspaceId],
      name: "artifact_versions_artifact_workspace_fk"
    }).onDelete("cascade"),
    unique("artifact_versions_artifact_version_unique").on(table.artifactId, table.version),
    index("artifact_versions_workspace_created_idx").on(table.workspaceId, table.createdAt),
    check("artifact_versions_version_check", sql`${table.version} > 0`),
    check("artifact_versions_byte_size_check", sql`${table.byteSize} >= 0`),
    check("artifact_versions_checksum_check", sql`${table.checksumSha256} ~ '^[0-9a-f]{64}$'`),
    check(
      "artifact_versions_content_location_check",
      sql`(${table.contentText} is not null and ${table.storageKey} is null) or (${table.contentText} is null and ${table.storageKey} is not null)`
    )
  ]
);

export const jobArtifacts = pgTable(
  "job_artifacts",
  {
    jobId: uuid("job_id").notNull(),
    artifactId: uuid("artifact_id").notNull(),
    workspaceId: uuid("workspace_id").notNull(),
    relation: text("relation").notNull().default("output"),
    createdAt: createdAt()
  },
  (table) => [
    primaryKey({ columns: [table.jobId, table.artifactId], name: "job_artifacts_pk" }),
    foreignKey({
      columns: [table.jobId, table.workspaceId],
      foreignColumns: [jobs.id, jobs.workspaceId],
      name: "job_artifacts_job_workspace_fk"
    }).onDelete("cascade"),
    foreignKey({
      columns: [table.artifactId, table.workspaceId],
      foreignColumns: [artifacts.id, artifacts.workspaceId],
      name: "job_artifacts_artifact_workspace_fk"
    }).onDelete("cascade"),
    check("job_artifacts_relation_check", sql`${table.relation} in ('output', 'attachment')`)
  ]
);

export const notifications = pgTable(
  "notifications",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    userId: uuid("user_id")
      .notNull()
      .references(() => users.id, { onDelete: "cascade" }),
    workspaceId: uuid("workspace_id")
      .notNull()
      .references(() => workspaces.id, { onDelete: "cascade" }),
    jobId: uuid("job_id"),
    artifactId: uuid("artifact_id"),
    type: text("type").notNull(),
    title: text("title").notNull(),
    body: text("body"),
    status: text("status").notNull().default("unread"),
    actionPath: text("action_path").notNull(),
    readAt: timestamp("read_at", { withTimezone: true, mode: "date" }),
    openedAt: timestamp("opened_at", { withTimezone: true, mode: "date" }),
    createdAt: createdAt(),
    updatedAt: updatedAt()
  },
  (table) => [
    foreignKey({
      columns: [table.jobId, table.workspaceId],
      foreignColumns: [jobs.id, jobs.workspaceId],
      name: "notifications_job_workspace_fk"
    }).onDelete("restrict"),
    foreignKey({
      columns: [table.artifactId, table.workspaceId],
      foreignColumns: [artifacts.id, artifacts.workspaceId],
      name: "notifications_artifact_workspace_fk"
    }).onDelete("restrict"),
    index("notifications_user_status_idx").on(table.userId, table.status, table.createdAt),
    check("notifications_status_check", sql`${table.status} in ('unread', 'read', 'archived')`),
    check("notifications_action_path_check", sql`${table.actionPath} like '/%'`)
  ]
);

export const auditEvents = pgTable(
  "audit_events",
  {
    id: uuid("id").primaryKey().defaultRandom(),
    actorUserId: uuid("actor_user_id").references(() => users.id, { onDelete: "set null" }),
    workspaceId: uuid("workspace_id").references(() => workspaces.id, { onDelete: "set null" }),
    eventType: text("event_type").notNull(),
    targetType: text("target_type"),
    targetId: uuid("target_id"),
    outcome: text("outcome").notNull().default("success"),
    requestId: text("request_id"),
    metadata: jsonb("metadata").$type<Record<string, unknown>>().notNull().default({}),
    createdAt: createdAt()
  },
  (table) => [
    index("audit_events_workspace_created_idx").on(table.workspaceId, table.createdAt),
    index("audit_events_actor_created_idx").on(table.actorUserId, table.createdAt),
    check("audit_events_outcome_check", sql`${table.outcome} in ('success', 'failure', 'denied')`)
  ]
);

export const readyDockItems = pgView("ready_dock_items", {
  id: uuid("id").notNull(),
  title: text("title").notNull(),
  workspaceId: uuid("workspace_id").notNull(),
  requestedByUserId: uuid("requested_by_user_id").notNull(),
  dockStatus: text("dock_status").notNull(),
  jobStatus: text("job_status").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true, mode: "date" }).notNull(),
  completedAt: timestamp("completed_at", { withTimezone: true, mode: "date" }),
  conversationId: uuid("conversation_id"),
  artifactId: uuid("artifact_id"),
  artifactVersion: integer("artifact_version"),
  approvalState: text("approval_state"),
  notificationId: uuid("notification_id"),
  actionPath: text("action_path"),
  isUnread: boolean("is_unread").notNull(),
  canApprove: boolean("can_approve").notNull(),
  canRevise: boolean("can_revise").notNull(),
  canArchive: boolean("can_archive").notNull()
}).existing();

export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
export type Session = typeof sessions.$inferSelect;
export type Workspace = typeof workspaces.$inferSelect;
export type WorkspaceMembership = typeof workspaceMemberships.$inferSelect;
export type Conversation = typeof conversations.$inferSelect;
export type Message = typeof messages.$inferSelect;
export type Job = typeof jobs.$inferSelect;
export type Artifact = typeof artifacts.$inferSelect;
export type ArtifactVersion = typeof artifactVersions.$inferSelect;
export type Notification = typeof notifications.$inferSelect;
export type AuditEvent = typeof auditEvents.$inferSelect;
