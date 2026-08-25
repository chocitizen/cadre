import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { BrandMark } from "@/components/brand-mark";
import { LoginForm } from "@/components/login-form";
import { getPageSession } from "@/server/auth";

export const metadata: Metadata = {
  title: "Sign in"
};
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export default async function LoginPage() {
  if (await getPageSession()) redirect("/app");

  return (
    <main className="auth-page" id="main-content">
      <header className="auth-header">
        <BrandMark />
        <span className="status status-canonical">Private command surface</span>
      </header>
      <section className="auth-content" aria-labelledby="login-title">
        <div className="auth-statement">
          <p className="section-label">Authority remains human</p>
          <h1 id="login-title">Return to the helm.</h1>
          <p>
            Enter the private workspace for governed conversations, durable work, approvals, and
            exact artifacts.
          </p>
        </div>
        <div className="auth-panel">
          <div>
            <h2>Owner access</h2>
            <p>Credentials are verified on the server. Sessions remain revocable and auditable.</p>
          </div>
          <LoginForm />
          <p className="auth-help">
            First run? Create the owner locally with <code>npm run owner:create</code> before
            signing in.
          </p>
        </div>
      </section>
      <footer className="auth-footer">
        <span>CADRE Foundation v0.1</span>
        <span>Doctrine governs · CADRE executes</span>
      </footer>
    </main>
  );
}
