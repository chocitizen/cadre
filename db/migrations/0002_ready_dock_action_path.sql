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
  COALESCE(n.action_path, CASE WHEN a.id IS NOT NULL THEN '/app/artifacts/' || a.id::text END) AS action_path,
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
