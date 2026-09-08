import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  clearToken,
  hasSession,
  isCookieMode,
  loadRefreshToken,
  loadToken,
  saveToken,
  saveTokenPair,
  setCookieMode,
} from "./auth";

describe("auth storage (lite transport)", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("round-trips a token pair through localStorage", () => {
    saveTokenPair("access-1", "refresh-1");
    expect(loadToken()).toBe("access-1");
    expect(loadRefreshToken()).toBe("refresh-1");
    clearToken();
    expect(loadToken()).toBeNull();
    expect(loadRefreshToken()).toBeNull();
  });

  it("saveToken stores only the access token", () => {
    saveToken("solo");
    expect(loadToken()).toBe("solo");
    expect(loadRefreshToken()).toBeNull();
  });

  it("dispatches the opengrow:auth event on save and clear", () => {
    const spy = vi.fn();
    window.addEventListener("opengrow:auth", spy);
    saveToken("a");
    clearToken();
    window.removeEventListener("opengrow:auth", spy);
    expect(spy).toHaveBeenCalledTimes(2);
  });
});

describe("cookie mode flag", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("starts in lite mode with no session", () => {
    expect(isCookieMode()).toBe(false);
    expect(hasSession()).toBe(false);
  });

  it("hasSession() reports authenticated once a token is stored", () => {
    saveToken("a");
    expect(hasSession()).toBe(true);
    clearToken();
    expect(hasSession()).toBe(false);
  });

  it("setCookieMode() flips the flag, dispatches the event once, and counts as a session", () => {
    const spy = vi.fn();
    window.addEventListener("opengrow:auth", spy);
    setCookieMode();
    setCookieMode();
    window.removeEventListener("opengrow:auth", spy);
    expect(isCookieMode()).toBe(true);
    expect(hasSession()).toBe(true);
    expect(spy).toHaveBeenCalledTimes(1);
  });
});
