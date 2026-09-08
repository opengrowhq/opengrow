<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Frontend testing

- Every new or changed UI functionality must ship with focused tests for the behavior or flow being changed.
- Prefer route/component/e2e coverage for user flows such as auth redirects and tenant dashboard actions. Checkout flows are not applicable — billing is hosted-only and not part of the open-source app.
- Manual screenshots and lint/build checks are useful validation, but do not replace automated tests unless no suitable harness exists yet; document that gap clearly.

## Auth transports (both must keep working)

`src/lib/auth.ts` + `src/lib/http.ts` support two session transports:

- **Lite**: Bearer tokens in localStorage (`opengrow.token` / `opengrow.refresh`).
- **Cookie mode**: the node-gateway BFF strips token pairs from login/refresh/invite-accept responses into httpOnly cookies and marks them `x-og-auth: cookie`; `readAuthMode()` flips the module-level flag.

Rules when touching auth code: never save a stripped (`pair: null`) login/invite result to localStorage; gate "am I logged in" checks on `hasSession()` (not `loadToken()`); every `fetch` to the API sends `credentials: "include"`; cookie-mode refresh treats `res.ok` as success (body is stripped); `ensureSession()` is the silent session restore the auth guard awaits before redirecting.
