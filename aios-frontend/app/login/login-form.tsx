"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/services/api-client";
import { Loader2 } from "lucide-react";

export function LoginForm({ next, demo }: { next: string; demo: { email: string; password: string } | null }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaCode, setMfaCode] = useState("");
  const [needsMfa, setNeedsMfa] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const router = useRouter();

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
        {demo && (
          <div className="mt-5 rounded-md border border-dashed border-border p-3 text-xs text-muted-foreground" aria-label="Demo account">
            <p>
              Public demo with synthetic data: <span className="font-mono text-foreground">{demo.email}</span> /{" "}
              <span className="font-mono text-foreground">{demo.password}</span>
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={() => {
                setEmail(demo.email);
                setPassword(demo.password);
              }}
            >
              Use demo account
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
