import { AppShell } from "@/components/app-shell";
import { requirePageSession } from "@/server/auth";
import { getDatabase } from "@/server/db";
import { listUserWorkspaces } from "@/server/data";

export const dynamic = "force-dynamic";

export default async function CadreLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const db = await getDatabase();
  const { user } = await requirePageSession(db);
  const workspaces = await listUserWorkspaces(db, user.id);

  return (
    <AppShell
      user={{
        id: user.id,
        email: user.email,
        displayName: user.displayName,
        role: user.role
      }}
      workspaces={workspaces}
    >
      {children}
    </AppShell>
  );
}
