import { test } from 'node:test';
import assert from 'node:assert/strict';
import { fetchInfisicalSecrets, InfisicalFetchError } from './infisical.js';

const OPTS = {
  url: 'https://infisical.example.com',
  projectId: 'proj-1',
  environment: 'dev',
  token: 'tok',
};

function withFetch(impl: typeof fetch, fn: () => Promise<void>): Promise<void> {
  const original = globalThis.fetch;
  globalThis.fetch = impl;
  return fn().finally(() => {
    globalThis.fetch = original;
  });
}

test('returns {} when no token is configured (lite mode)', async () => {
  const secrets = await fetchInfisicalSecrets({ ...OPTS, token: '' });
  assert.deepEqual(secrets, {});
});

test('parses secrets on success', async () => {
  await withFetch(
    (async () =>
      new Response(
        JSON.stringify({
          secrets: [
            { secretKey: 'JWT_SECRET', secretValue: 's3cret' },
            { secretKey: 'OTHER', secretValue: 'x' },
          ],
        }),
        { status: 200 },
      )) as typeof fetch,
    async () => {
      const secrets = await fetchInfisicalSecrets(OPTS);
      assert.equal(secrets.JWT_SECRET, 's3cret');
      assert.equal(secrets.OTHER, 'x');
    },
  );
});

test('throws on HTTP error status when configured', async () => {
  await withFetch(
    (async () => new Response('unauthorized', { status: 401 })) as typeof fetch,
    async () => {
      await assert.rejects(() => fetchInfisicalSecrets(OPTS), InfisicalFetchError);
    },
  );
});

test('throws on network failure when configured', async () => {
  await withFetch(
    (async () => {
      throw new TypeError('fetch failed');
    }) as typeof fetch,
    async () => {
      await assert.rejects(() => fetchInfisicalSecrets(OPTS), InfisicalFetchError);
    },
  );
});
