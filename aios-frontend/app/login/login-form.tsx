"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/services/api-client";
import { Loader2 } from "lucide-react";

export function LoginForm({ next, guest }: { next: string; guest: boolean }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [needsMfa, setNeedsMfa] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function exploreDemo() {
    setBusy(true);
    setError(null);
    try {
      await api("/api/auth/guest", { method: "POST", body: {} });
      router.replace(next);
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not start a demo session.");
    } finally {
      setBusy(false);
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/auth/login", { method: "POST", body: { email, password, mfa_code: mfaCode || undefined } });
      router.replace(next);
      router.refresh();
    } catch (err) {
      if (err instanceof ApiError && err.message && /multi-factor/i.test(err.message)) {
        setNeedsMfa(true);
        setError(mfaCode ? "That code didn't work. Try the current one from your authenticator." : null);
      } else {
        setError(err instanceof ApiError ? err.message : "Sign-in failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="w-full max-w-sm">
      <CardHeader>
        <CardTitle className="text-xl">Sign in to AIOS</CardTitle>
        <CardDescription>Your session is kept in a secure, httpOnly cookie; no token reaches this page.</CardDescription>
      </CardHeader>
      <CardContent>
        {guest && (
          <div className="mb-5 space-y-3">
            <Button type="button" className="w-full" onClick={() => void exploreDemo()} disabled={busy}>
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Explore the live demo
            </Button>
            <p className="text-xs leading-relaxed text-muted-foreground">
              Opens the Northwind Operations demo organisation (synthetic data) as an ordinary member: agents, prompts,
              workflows, tools, evaluations and the live health of all twenty services. No administration, and the demo
              resets when the server restarts.
            </p>
            <div className="flex items-center gap-3 text-xs text-muted-foreground" aria-hidden>
              <span className="h-px flex-1 bg-border" />
              or
              <span className="h-px flex-1 bg-border" />
            </div>
          </div>
        )}
        <form onSubmit={submit} className="space-y-4" aria-label="Sign in">
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          {needsMfa && (
            <div className="space-y-1.5">
              <Label htmlFor="mfa">Authentication code</Label>
              <Input id="mfa" inputMode="numeric" autoComplete="one-time-code" value={mfaCode} onChange={(e) => setMfaCode(e.target.value)} autoFocus />
              <p className="text-xs text-muted-foreground">Enter the 6-digit code from your authenticator app, or a recovery code.</p>
            </div>
          )}
          {error && (
            <p role="alert" className="text-sm text-destructive">
              {error}
            </p>
          )}
          <Button type="submit" className="w-full" disabled={busy || !email || !password}>
            {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
