import { demoAccount } from "@/lib/server/config";
import { safeNextPath } from "@/lib/safe-next";
import { LoginForm } from "./login-form";

export const dynamic = "force-dynamic";

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const { next } = await searchParams;
  const safeNext = safeNextPath(next);
  return (
    <main className="flex min-h-screen items-center justify-center bg-muted/30 px-4">
      <LoginForm next={safeNext} demo={demoAccount()} />
    </main>
  );
}
