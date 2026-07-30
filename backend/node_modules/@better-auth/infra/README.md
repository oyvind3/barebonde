# Better Auth Infrastructure

Infra plugins for Better Auth:

- `dash()` for dashboard/admin APIs, analytics tracking, and infra endpoints.
- `dashClient()` for dashboard client actions (including audit log queries).
- `sentinel()` for security checks and abuse protection.
- `sentinelClient()` for browser fingerprint headers + optional PoW auto-solving.
- `sentinelNativeClient()` (from `@better-auth/infra/native`) for React Native / Expo.

## Installation

```bash
npm install @better-auth/infra
# or
pnpm add @better-auth/infra
# or
bun add @better-auth/infra
```

## Server Usage

```ts
import { betterAuth } from "better-auth";
import { dash, sentinel } from "@better-auth/infra";

export const auth = betterAuth({
  // ...your Better Auth config
  plugins: [
    dash({
      apiUrl: process.env.BETTER_AUTH_API_URL,
      kvUrl: process.env.BETTER_AUTH_KV_URL,
      apiKey: process.env.BETTER_AUTH_API_KEY,
    }),
    sentinel({
      apiUrl: process.env.BETTER_AUTH_API_URL,
      kvUrl: process.env.BETTER_AUTH_KV_URL,
      apiKey: process.env.BETTER_AUTH_API_KEY,
      security: {
        credentialStuffing: {
          enabled: true,
          thresholds: { challenge: 3, block: 5 },
        },
      },
    }),
  ],
});
```

## Client Usage

```ts
import { createAuthClient } from "better-auth/client";
import { dashClient, sentinelClient } from "@better-auth/infra/client";

export const authClient = createAuthClient({
  plugins: [
    dashClient(),
    sentinelClient({
      autoSolveChallenge: true,
    }),
  ],
});

// Resolve user from session or pass explicit user/org context
const auditLogs = await authClient.dash.getAuditLogs({
  session: await authClient.getSession().then((r) => r.data),
  organizationId: "org_123",
  limit: 20,
});
```

## Native client

Use this plugin for your React Native / Expo app. This plugin is designed to work along with the server side sentinel and dash plugins and will ensure your app is protected from abuse and bot attacks.

### Install peers

```bash
pnpm add react-native @react-native-async-storage/async-storage
# Optional, for richer device metadata in the identify payload:
pnpm add expo-constants expo-device
```

`@react-native-async-storage/async-storage` is optional; if it is not installed, a session-only in-memory visitor id is used. For production, install it or pass `storage` (for example secure storage).

### Example

```ts
import { createAuthClient } from "better-auth/client";
import { dashClient, sentinelNativeClient } from "@better-auth/infra/native";

export const authClient = createAuthClient({
  baseURL: "https://your-api.example.com",
  plugins: [
    dashClient(),
    sentinelNativeClient({
      identifyUrl: process.env.EXPO_PUBLIC_BETTER_AUTH_KV_URL,
      autoSolveChallenge: true,
    }),
  ],
});
```

### Options (`sentinelNativeClient`)

- `identifyUrl?: string` — KV identify endpoint base (defaults to `BETTER_AUTH_KV_URL` from env, then `https://kv.better-auth.com`).
- `autoSolveChallenge?: boolean` — When `true` (default), `423` responses that include `X-PoW-Challenge` are solved and the request is retried once with `X-PoW-Solution`.
- `onChallengeReceived?` / `onChallengeSolved?` / `onChallengeFailed?` — PoW lifecycle hooks (reason string, solve time in ms, or error).
- `storage?: { getItem, setItem }` — Async key/value storage for a stable per-install visitor id (recommended for production).

## Audit Log APIs

### `dashClient()` API

`dashClient()` adds:

- `authClient.dash.getAuditLogs(input)`

`getAuditLogs(input)` accepts:

- `limit?: number` (default `50`, max `100`)
- `offset?: number` (default `0`)
- `organizationId?: string`
- `identifier?: string`
- `eventType?: string`
- `userId?: string`
- `user?: { id?: string | null }`
- `session?: { user?: { id?: string | null } }`

The resolved user ID is determined in this order:

- `input.userId`
- `dashClient({ resolveUserId })`
- `input.user?.id`
- `input.session?.user?.id`

Response shape:

- `events: DashAuditLog[]`
- `total: number`
- `limit: number`
- `offset: number`

Example:

```ts
const session = await authClient.getSession().then((r) => r.data);

const logs = await authClient.dash.getAuditLogs({
  session,
  organizationId: "org_123",
  limit: 50,
  offset: 0,
});
```

To fetch all events, keep paginating with `offset` until `events.length < limit`.

### Filtering

Use `getAuditLogs` filters directly in the query:

- `eventType`: only return a specific event type (for example `user_signed_in`)
- `organizationId`: scope logs to one organization
- `identifier`: narrow organization logs to a specific identifier
- `userId` / `user` / `session`: resolve which user the logs should be scoped to

Examples:

```ts
// 1) Filter by event type
const signIns = await authClient.dash.getAuditLogs({
  session,
  eventType: "user_signed_in",
  limit: 20,
});

// 2) Filter by org + identifier
const orgMemberEvents = await authClient.dash.getAuditLogs({
  session,
  organizationId: "org_123",
  identifier: "user@example.com",
  limit: 50,
});

// 3) Combine filters
const orgSignIns = await authClient.dash.getAuditLogs({
  session,
  organizationId: "org_123",
  eventType: "user_signed_in",
  limit: 50,
});
```

### Search Patterns

`getAuditLogs` does not currently expose a dedicated full-text `search` query param.
For text search, fetch pages and filter client-side.

```ts
const matchesText = (event: { eventType: string; eventKey: string; eventData: Record<string, unknown> }, query: string) => {
  const q = query.toLowerCase().trim();
  if (!q) return true;

  const haystack = [
    event.eventType,
    event.eventKey,
    JSON.stringify(event.eventData ?? {}),
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(q);
};

const page = await authClient.dash.getAuditLogs({ session, limit: 100, offset: 0 });
const filtered = page.data?.events.filter((event) => matchesText(event, "password")) ?? [];
```

You can apply the same pattern for:

- date range filtering (by `createdAt`)
- location filtering (by `location.country`, `location.city`, etc.)
- multi-field compound filters

### Pagination Helper

```ts
async function getAllAuditLogs(session: unknown) {
  const limit = 100;
  let offset = 0;
  const all: Array<{
    eventType: string;
    createdAt: string;
    eventData: Record<string, unknown>;
  }> = [];

  while (true) {
    const result = await authClient.dash.getAuditLogs({ session, limit, offset });
    const events = result.data?.events ?? [];
    all.push(...events);

    if (events.length < limit) break;
    offset += limit;
  }

  return all;
}
```

### `dash()` Event Endpoints

The `dash()` plugin registers these event endpoints:

- `getUserEvents` on `GET /events/list`
- `getAuditLogs` on `GET /events/audit-logs`
- `getEventTypes` on `GET /events/types`

`getAuditLogs` supports query params:

- `limit`, `offset`, `eventType`
- `organizationId`, `identifier`
- `userId` (must match the authenticated session user)

## Option Types

### `DashOptions`

- `apiUrl?: string`
- `kvUrl?: string`
- `apiKey?: string`
- `activityTracking?: { enabled?: boolean; updateInterval?: number }`

`dash()` no longer accepts sentinel security config.

### `SentinelOptions`

- `apiUrl?: string`
- `kvUrl?: string`
- `apiKey?: string`
- `security?: SecurityOptions`

All security configuration now belongs in `sentinel()`.

### `DashClientOptions`

- `resolveUserId?: ({ userId, user, session }) => string | undefined`

See `Audit Log APIs` above for full method details.

### `SentinelNativeClientOptions`

Exported from `@better-auth/infra/native`. See [React Native client](#native-client) for the full option list and usage.

## Migration

If you previously passed security config to `dash()`, move it to `sentinel()`:

```ts
// before
dash({
  apiKey: process.env.BETTER_AUTH_API_KEY,
  // no longer supported in dash
  security: {
    credentialStuffing: { enabled: true },
  },
});

// after
dash({ apiKey: process.env.BETTER_AUTH_API_KEY });
sentinel({
  apiKey: process.env.BETTER_AUTH_API_KEY,
  security: {
    credentialStuffing: { enabled: true },
  },
});
```

## Security Notes

- Use `sentinel()` to enforce security checks. `dash()` is focused on telemetry/admin behavior.
- Provide `BETTER_AUTH_API_KEY`; without it, sentinel cannot securely call infra APIs and will warn at startup.
- If you run behind a proxy/CDN, validate your upstream header trust model (`x-forwarded-for`, etc.) to avoid spoofed client IP attribution.
