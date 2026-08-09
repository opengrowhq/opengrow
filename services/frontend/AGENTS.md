<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Frontend testing

- Every new or changed UI functionality must ship with focused tests for the behavior or flow being changed.
- Prefer route/component/e2e coverage for user flows such as auth redirects, pricing checkout, and tenant dashboard actions.
- Manual screenshots and lint/build checks are useful validation, but do not replace automated tests unless no suitable harness exists yet; document that gap clearly.
