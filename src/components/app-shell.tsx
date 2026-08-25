"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { BrandMark } from "@/components/brand-mark";
import { LogoutButton } from "@/components/logout-button";
import type { SessionUser, WorkspaceSummary } from "@/lib/types";

function NavLink({
  href,
  label,
  onNavigate
}: {
  href: string;
  label: string;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const active = pathname === href || (href !== "/app" && pathname.startsWith(`${href}/`));

  return (
    <Link
      className={active ? "nav-link nav-link-active" : "nav-link"}
      href={href}
      onClick={onNavigate}
    >
      {label}
    </Link>
  );
}

function RailContent({
  user,
  workspaces,
  onNavigate
}: {
  user: SessionUser;
  workspaces: WorkspaceSummary[];
  onNavigate?: () => void;
}) {
  return (
    <>
      <div className="rail-brand">
        <BrandMark />
      </div>
      <nav className="rail-nav" aria-label="Primary navigation">
        <div className="nav-section">
          <span className="nav-heading">Command</span>
          <NavLink href="/app" label="Overview" onNavigate={onNavigate} />
          <NavLink href="/app/ready" label="Ready Dock" onNavigate={onNavigate} />
          <NavLink href="/app/audit" label="Audit trail" onNavigate={onNavigate} />
        </div>
        <div className="nav-section nav-workspaces">
          <span className="nav-heading">Workspaces</span>
          {workspaces.map((workspace) => (
            <NavLink
              href={`/app/w/${workspace.slug}`}
              key={workspace.id}
              label={workspace.name}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      </nav>
      <div className="rail-user">
        <span className="user-avatar" aria-hidden="true">
          {user.displayName.slice(0, 1).toUpperCase()}
        </span>
        <span className="user-identity">
          <strong>{user.displayName}</strong>
          <small>{user.role}</small>
        </span>
        <LogoutButton compact />
      </div>
    </>
  );
}

export function AppShell({
  user,
  workspaces,
  children
}: {
  user: SessionUser;
  workspaces: WorkspaceSummary[];
  children: React.ReactNode;
}) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="app-shell">
      <aside className="rail">
        <RailContent user={user} workspaces={workspaces} />
      </aside>

      <header className="mobile-header">
        <BrandMark compact />
        <button
          aria-controls="mobile-navigation"
          aria-expanded={drawerOpen}
          className="button button-secondary mobile-menu-button"
          onClick={() => setDrawerOpen((open) => !open)}
          type="button"
        >
          {drawerOpen ? "Close" : "Menu"}
        </button>
      </header>

      {drawerOpen && (
        <div className="mobile-drawer-backdrop" onClick={() => setDrawerOpen(false)}>
          <aside
            aria-label="Mobile navigation"
            aria-modal="true"
            className="mobile-drawer"
            id="mobile-navigation"
            onClick={(event) => event.stopPropagation()}
            role="dialog"
          >
            <RailContent
              onNavigate={() => setDrawerOpen(false)}
              user={user}
              workspaces={workspaces}
            />
          </aside>
        </div>
      )}

      <main className="work-surface" id="main-content">
        {children}
      </main>
    </div>
  );
}
