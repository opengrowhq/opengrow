import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isPublicPath, pathnameOf } from './public-paths.js';

test('login, tracking, and health are public', () => {
  assert.equal(isPublicPath('/auth/login'), true);
  assert.equal(isPublicPath('/analytics/pixel.gif'), true);
  assert.equal(isPublicPath('/analytics/track'), true);
  assert.equal(isPublicPath('/health'), true);
  assert.equal(isPublicPath('/ready'), true);
});

test('sensitive routes require auth at the edge', () => {
  assert.equal(isPublicPath('/auth/me'), false);
  assert.equal(isPublicPath('/content'), false);
  assert.equal(isPublicPath('/content/abc'), false);
  assert.equal(isPublicPath('/analytics/summary'), false);
  assert.equal(isPublicPath('/analytics/events'), false);
  assert.equal(isPublicPath('/assets'), false);
  assert.equal(isPublicPath('/generations'), false);
  assert.equal(isPublicPath('/brands'), false);
});

test('pathnameOf strips the query string', () => {
  assert.equal(pathnameOf('/analytics/pixel.gif?tenant=demo&x=1'), '/analytics/pixel.gif');
  assert.equal(pathnameOf('/content'), '/content');
});
