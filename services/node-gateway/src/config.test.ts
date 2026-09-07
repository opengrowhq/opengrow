import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadConfig } from './config.js';

function withEnv(patch: Record<string, string>, fn: () => Promise<void>): Promise<void> {
  const originals: Record<string, string | undefined> = {};
  for (const [k, v] of Object.entries(patch)) {
    originals[k] = process.env[k];
    process.env[k] = v;
  }
  return fn().finally(() => {
    for (const [k, v] of Object.entries(originals)) {
      if (v === undefined) delete process.env[k];
      else process.env[k] = v;
    }
  });
}

function withFetch(impl: typeof fetch, fn: () => Promise<void>): Promise<void> {
  const original = globalThis.fetch;
  globalThis.fetch = impl;
  return fn().finally(() => {
    globalThis.fetch = original;
  });
}

const INFISICAL_ENV = {
  INFISICAL_URL: 'https://infisical.example.com',
  INFISICAL_PROJECT_ID: 'proj-1',
  INFISICAL_ENVIRONMENT: 'dev',
  INFISICAL_TOKEN: 'tok',
};

test('boot fails when Infisical is configured but returns no JWT_SECRET', async () => {
  await withEnv(INFISICAL_ENV, () =>
    withFetch(
      (async () =>
        new Response(JSON.stringify({ secrets: [] }), { status: 200 })) as typeof fetch,
      async () => {
        await assert.rejects(() => loadConfig(), /returned no JWT_SECRET/);
      },
    ),
  );
});

test('boot succeeds when Infisical returns a JWT_SECRET', async () => {
  await withEnv(INFISICAL_ENV, () =>
    withFetch(
      (async () =>
        new Response(
          JSON.stringify({ secrets: [{ secretKey: 'JWT_SECRET', secretValue: 's3cret' }] }),
          { status: 200 },
        )) as typeof fetch,
      async () => {
        const cfg = await loadConfig();
        assert.equal(cfg.jwtSecret, 's3cret');
      },
    ),
  );
});

test('lite mode (no INFISICAL_TOKEN) boots without contacting Infisical', async () => {
  await withEnv(
    {
      INFISICAL_URL: 'https://infisical.example.com',
      INFISICAL_PROJECT_ID: 'proj-1',
      INFISICAL_ENVIRONMENT: 'dev',
      INFISICAL_TOKEN: '',
    },
    () =>
      withFetch(
        (async () => {
          throw new Error('fetch must not be called in lite mode');
        }) as typeof fetch,
        async () => {
          const cfg = await loadConfig();
          assert.equal(cfg.jwtSecret, '');
        },
      ),
  );
});
