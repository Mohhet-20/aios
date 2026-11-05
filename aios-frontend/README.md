# aios-frontend: the AIOS console

Next.js 16 (App Router), React 19 and TypeScript. The console is two things in one deployable:

- **The edge** (`app/api/*`, `lib/server/*`, `proxy.ts`): a backend-for-frontend that signs users in through the
  identity service, keeps the session in httpOnly cookies, verifies the access token on every call and talks to the
  domain services server-to-server with the internal token and the verified user id.
- **The UI** (`app/(shell)/*`, `features/*`, `components/*`): pages built on Radix primitives, Tailwind CSS and
  TanStack Query.

## How a request flows

1. `proxy.ts` sends visitors without a session cookie to `/login` (routing only; it never trusts the cookie).
2. `POST /api/auth/login` calls the identity service's `/auth/token` (password, then MFA when enrolled) and writes
   `aios_at` (15 min) and `aios_rt` (30 days) as httpOnly, SameSite=Lax cookies, Secure in production.
3. Every `/api/console/*` route runs inside `withSession` (`lib/server/route.ts`): `getSession`
   (`lib/server/session.ts`) verifies the access token with `jose` (HS256), rotates it through the identity service's
   refresh endpoint when it has expired, and returns 401 when there is no valid session.
4. `lib/server/console.ts` resolves the caller's organisation to each service's workspace (`workspaceFor`, cached for a
   minute), calls the service through `callService` (`lib/server/services.ts`: internal token, user id, timeout,
   both error formats) and normalises the records into the shapes in `types/live.ts`.
5. The pages read them with the hooks in `services/console.ts`. `LiveState` and `LiveTable` render loading, error and
   empty states, so a service failure is shown, never hidden.

| Route | Purpose |
|---|---|
| `POST /api/auth/login` · `POST /api/auth/logout` · `GET /api/auth/session` | sign-in, server-side revocation, the signed-in user and organisation |
| `GET /api/console/overview` | counts from five services plus readiness of all twenty |
| `GET /api/console/status` | readiness and measured latency of every service |
| `GET /api/console/{agents,prompts,workflows,tools,evaluations,datasets,models}` | normalised lists |
| `POST /api/console/generate` | one completion through the AI Core gateway, latency measured at the edge |

## Live and preview pages

Dashboard, Agents, Prompt Library, Workflows, Tools, Evaluation, Model Registry and Model Playground are live
(`LIVE_ROUTES` in `components/shared/preview-banner.tsx`). Every other route shows a "Preview: illustrative data"
banner automatically, so a new page is labelled until someone wires it and adds it to the list. Their fixtures live
in `lib/mock-data.ts`.

## Configuration (server-side only)

| Variable | Purpose |
|---|---|
| `AIOS_<SERVICE>_URL` | base URL of each service, e.g. `AIOS_AGENT_URL`; defaults to the local ports `scripts/dev.py` uses |
| `AIOS_INTERNAL_TOKEN` | sent as `X-Internal-Token`; must match the services' value |
| `AIOS_JWT_SECRET` | the identity service's `SECRET_KEY`; required in production |
| `AIOS_SERVICES_BASE_URL` | all services behind one host as `<base>/<service>` (the hosted demo); a per-service URL still wins |
| `AIOS_GUEST_ACCESS` | `true` on a hosted demo: the sign-in page offers *Explore the live demo* (identity's `/auth/guest`); no password is ever shown |

Nothing here is a `NEXT_PUBLIC_` variable: no secret or service URL reaches the browser bundle.

## Develop and test

```bash
npm ci
npm run dev                                          # http://localhost:3000 (services from scripts/dev.py)
npm run typecheck && npm run lint && npm test && npm run build
```

The unit tests (`tests/unit`) cover the route guard, the open-redirect check, `callService` (headers, both error
formats, unreachable services), the live-state UI, preview labelling and date handling. The repository root's README
describes the system-level smoke test and the browser walkthrough.

## Notes

- `next/font/google` is replaced by a system font stack, so the build doesn't need network access to Google Fonts.
- Inference Studio uses a client-side streaming simulator (`hooks/use-streaming-completion.ts`) and is labelled as a
  preview; the Model Playground is the real path to AI Core.
