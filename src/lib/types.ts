export type WorkspaceSummary = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  status: string;
};

export type SessionUser = {
  id: string;
  email: string;
  displayName: string;
  role: "owner" | "admin" | "member";
};

export type ConversationSummary = {
  id: string;
  workspaceId: string;
  title: string;
  status: string;
  model: string | null;
  provider: string | null;
  createdAt: string;
  updatedAt: string;
};

export type MessageDto = {
  id: string;
  conversationId: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  provider: string | null;
  model: string | null;
  createdAt: string;
};

export type ConversationDetail = {
  conversation: ConversationSummary;
  workspace: WorkspaceSummary;
  messages: MessageDto[];
};

export type ArtifactSummary = {
  id: string;
  workspaceId: string;
  conversationId: string | null;
  jobId: string | null;
  title: string;
  type: string;
  currentVersion: number;
  approvalState: string;
  checksum?: string;
  content?: string;
  createdAt: string;
  updatedAt: string;
};

export type ReadyDockItem = {
  jobId: string;
  title: string;
  workspaceId: string;
  workspaceName: string;
  workspaceSlug: string;
  status: string;
  createdAt: string;
  completedAt: string | null;
  conversationId: string | null;
  artifactId: string | null;
  artifactVersion: number | null;
  approvalState: string | null;
  actionPath: string | null;
};

export type ApiError = {
  error: {
    code: string;
    message: string;
  };
};
