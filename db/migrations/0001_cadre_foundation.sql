CREATE TABLE IF NOT EXISTS users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text NOT NULL,
  display_name text NOT NULL,
  password_hash text NOT NULL,
  role text NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
  last_login_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT users_email_normalized_check CHECK (email = lower(btrim(email)))
);

CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_unique ON users (lower(email));

CREATE TABLE IF NOT EXISTS sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash text NOT NULL,
  csrf_token_hash text NOT NULL,
  user_agent_hash text,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  idle_expires_at timestamptz NOT NULL,
  absolute_expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  CONSTRAINT sessions_expiry_order_check CHECK (idle_expires_at <= absolute_expires_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS sessions_token_hash_unique ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS sessions_user_active_idx ON sessions(user_id, revoked_at, idle_expires_at);

CREATE TABLE IF NOT EXISTS auth_throttles (
  identifier_hash text PRIMARY KEY,
  attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  window_started_at timestamptz NOT NULL DEFAULT now(),
  blocked_until timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS workspaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug text NOT NULL UNIQUE,
  name text NOT NULL,
  description text,
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT workspaces_slug_check CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$')
);

CREATE TABLE IF NOT EXISTS workspace_memberships (
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role text NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT workspace_memberships_pk PRIMARY KEY (workspace_id, user_id)
);

CREATE INDEX IF NOT EXISTS workspace_memberships_user_idx ON workspace_memberships(user_id);

CREATE TABLE IF NOT EXISTS conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  created_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  title text NOT NULL DEFAULT 'Untitled conversation',
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  provider text,
  model text,
  last_message_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT conversations_id_workspace_unique UNIQUE (id, workspace_id)
);

CREATE INDEX IF NOT EXISTS conversations_workspace_recent_idx
  ON conversations(workspace_id, last_message_at);

CREATE TABLE IF NOT EXISTS messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL,
  conversation_id uuid NOT NULL,
  sequence integer NOT NULL CHECK (sequence > 0),
  role text NOT NULL CHECK (role IN ('user', 'assistant', 'system', 'tool')),
  content_text text NOT NULL,
  structured_content jsonb,
  created_by_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  status text NOT NULL DEFAULT 'completed' CHECK (status IN ('pending', 'completed', 'failed')),
  provider text,
  model text,
  provider_response_id text,
  prompt_key text,
  prompt_version integer,
  input_tokens integer CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens integer CHECK (output_tokens IS NULL OR output_tokens >= 0),
  retrieval_context jsonb,
  client_request_id text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT messages_conversation_workspace_fk
    FOREIGN KEY (conversation_id, workspace_id)
    REFERENCES conversations(id, workspace_id)
    ON DELETE CASCADE,
  CONSTRAINT messages_conversation_sequence_unique UNIQUE (conversation_id, sequence),
  CONSTRAINT messages_conversation_client_request_unique UNIQUE (conversation_id, client_request_id)
);

CREATE INDEX IF NOT EXISTS messages_conversation_created_idx
  ON messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  conversation_id uuid,
  requested_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  operation text NOT NULL,
  execution_mode text NOT NULL DEFAULT 'inline' CHECK (execution_mode IN ('inline', 'worker')),
  status text NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued', 'running', 'needs_approval', 'review', 'ready', 'failed', 'delivered', 'archived')),
  progress integer NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
  input_metadata jsonb,
  output_metadata jsonb,
  error_code text,
  error_message text,
  idempotency_key text,
  surface_in_ready_dock boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  started_at timestamptz,
  completed_at timestamptz,
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT jobs_id_workspace_unique UNIQUE (id, workspace_id),
  CONSTRAINT jobs_workspace_idempotency_unique UNIQUE (workspace_id, idempotency_key),
  CONSTRAINT jobs_conversation_workspace_fk
    FOREIGN KEY (conversation_id, workspace_id)
    REFERENCES conversations(id, workspace_id)
    ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS jobs_workspace_status_idx ON jobs(workspace_id, status, created_at);

CREATE TABLE IF NOT EXISTS artifacts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  conversation_id uuid,
  source_job_id uuid,
  created_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  title text NOT NULL,
  kind text NOT NULL,
  current_version integer NOT NULL DEFAULT 1 CHECK (current_version > 0),
  approval_state text NOT NULL DEFAULT 'draft'
    CHECK (approval_state IN ('draft', 'review', 'approved', 'rejected', 'archived')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT artifacts_id_workspace_unique UNIQUE (id, workspace_id),
  CONSTRAINT artifacts_conversation_workspace_fk
    FOREIGN KEY (conversation_id, workspace_id)
    REFERENCES conversations(id, workspace_id)
    ON DELETE RESTRICT,
  CONSTRAINT artifacts_source_job_workspace_fk
    FOREIGN KEY (source_job_id, workspace_id)
    REFERENCES jobs(id, workspace_id)
    ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS artifacts_workspace_updated_idx ON artifacts(workspace_id, updated_at);

CREATE TABLE IF NOT EXISTS artifact_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  artifact_id uuid NOT NULL,
  workspace_id uuid NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  content_text text,
  storage_provider text NOT NULL DEFAULT 'postgres',
  storage_key text,
  mime_type text NOT NULL,
  byte_size integer NOT NULL CHECK (byte_size >= 0),
  checksum_sha256 text NOT NULL CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),
  provenance jsonb NOT NULL,
  created_by_user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT artifact_versions_artifact_workspace_fk
    FOREIGN KEY (artifact_id, workspace_id)
    REFERENCES artifacts(id, workspace_id)
    ON DELETE CASCADE,
  CONSTRAINT artifact_versions_artifact_version_unique UNIQUE (artifact_id, version),
  CONSTRAINT artifact_versions_content_location_check CHECK (
    (content_text IS NOT NULL AND storage_key IS NULL)
    OR (content_text IS NULL AND storage_key IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS artifact_versions_workspace_created_idx
  ON artifact_versions(workspace_id, created_at);

CREATE TABLE IF NOT EXISTS job_artifacts (
  job_id uuid NOT NULL,
  artifact_id uuid NOT NULL,
  workspace_id uuid NOT NULL,
  relation text NOT NULL DEFAULT 'output' CHECK (relation IN ('output', 'attachment')),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT job_artifacts_pk PRIMARY KEY (job_id, artifact_id),
  CONSTRAINT job_artifacts_job_workspace_fk
    FOREIGN KEY (job_id, workspace_id)
    REFERENCES jobs(id, workspace_id)
    ON DELETE CASCADE,
  CONSTRAINT job_artifacts_artifact_workspace_fk
    FOREIGN KEY (artifact_id, workspace_id)
    REFERENCES artifacts(id, workspace_id)
    ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS notifications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  job_id uuid,
  artifact_id uuid,
  type text NOT NULL,
  title text NOT NULL,
  body text,
  status text NOT NULL DEFAULT 'unread' CHECK (status IN ('unread', 'read', 'archived')),
  action_path text NOT NULL CHECK (action_path LIKE '/%'),
  read_at timestamptz,
  opened_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT notifications_job_workspace_fk
    FOREIGN KEY (job_id, workspace_id)
    REFERENCES jobs(id, workspace_id)
    ON DELETE RESTRICT,
  CONSTRAINT notifications_artifact_workspace_fk
    FOREIGN KEY (artifact_id, workspace_id)
    REFERENCES artifacts(id, workspace_id)
    ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS notifications_user_status_idx
  ON notifications(user_id, status, created_at);

CREATE TABLE IF NOT EXISTS audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id uuid REFERENCES users(id) ON DELETE SET NULL,
  workspace_id uuid REFERENCES workspaces(id) ON DELETE SET NULL,
  event_type text NOT NULL,
  target_type text,
  target_id uuid,
  outcome text NOT NULL DEFAULT 'success' CHECK (outcome IN ('success', 'failure', 'denied')),
  request_id text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS audit_events_workspace_created_idx
  ON audit_events(workspace_id, created_at);
CREATE INDEX IF NOT EXISTS audit_events_actor_created_idx
  ON audit_events(actor_user_id, created_at);

CREATE OR REPLACE VIEW ready_dock_items AS
SELECT
  j.id,
  COALESCE(a.title, j.operation) AS title,
  j.workspace_id,
  j.requested_by_user_id,
  CASE j.status
    WHEN 'queued' THEN 'scheduled'
    WHEN 'running' THEN 'in_progress'
    WHEN 'needs_approval' THEN 'needs_approval'
    WHEN 'review' THEN 'needs_approval'
    WHEN 'ready' THEN 'ready'
    WHEN 'delivered' THEN 'ready'
    WHEN 'failed' THEN 'failed'
    WHEN 'archived' THEN 'archived'
  END AS dock_status,
  j.status AS job_status,
  j.created_at,
  j.completed_at,
  j.conversation_id,
  a.id AS artifact_id,
  a.current_version AS artifact_version,
  a.approval_state,
  n.id AS notification_id,
  COALESCE(n.action_path, CASE WHEN a.id IS NOT NULL THEN '/artifacts/' || a.id::text END) AS action_path,
  COALESCE(n.status = 'unread', false) AS is_unread,
  COALESCE(a.approval_state IN ('draft', 'review'), false) AS can_approve,
  COALESCE(a.approval_state <> 'archived', false) AS can_revise,
  j.status <> 'archived' AS can_archive
FROM jobs j
LEFT JOIN LATERAL (
  SELECT artifact.*
  FROM job_artifacts link
  JOIN artifacts artifact
    ON artifact.id = link.artifact_id
   AND artifact.workspace_id = link.workspace_id
  WHERE link.job_id = j.id
    AND link.workspace_id = j.workspace_id
    AND link.relation = 'output'
  ORDER BY artifact.updated_at DESC, artifact.id
  LIMIT 1
) a ON true
LEFT JOIN LATERAL (
  SELECT notification.*
  FROM notifications notification
  WHERE notification.job_id = j.id
    AND notification.workspace_id = j.workspace_id
    AND notification.user_id = j.requested_by_user_id
  ORDER BY notification.created_at DESC, notification.id
  LIMIT 1
) n ON true
WHERE j.surface_in_ready_dock = true;

INSERT INTO workspaces (slug, name, description)
VALUES
  ('cadre-governance', 'CADRE Governance', 'Parent-platform governance and doctrine operations.'),
  ('vessel', 'VESSEL', 'Flagship workspace reserved for future VESSEL services.'),
  ('chozen-voyage', 'CHOZEN Voyage', 'CHOZEN Voyage projects and operations.'),
  ('majestic-lifestyle', 'Majestic Lifestyle', 'Majestic Lifestyle projects and operations.'),
  ('majic-by-majestic', 'Majic by Majestic', 'Majic by Majestic projects and operations.'),
  ('breathe-deepr', 'Breathe DEEPR', 'Breathe DEEPR projects and operations.'),
  ('sirrah-publishing', 'Sirrah Publishing', 'Sirrah Publishing projects and operations.'),
  ('incubator', 'Incubator', 'Governed workspace for future initiatives.')
ON CONFLICT (slug) DO NOTHING;
