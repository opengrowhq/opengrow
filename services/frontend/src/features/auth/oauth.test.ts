import { describe, it, expect } from "vitest";
import { parseOAuthFragment } from "./oauth";

describe("parseOAuthFragment", () => {
  it("parses access + refresh tokens from the callback hash", () => {
    expect(parseOAuthFragment("#access_token=a&refresh_token=r")).toEqual({
      access_token: "a",
      refresh_token: "r",
    });
  });

  it("accepts a pair without a refresh token", () => {
    expect(parseOAuthFragment("#access_token=a")).toEqual({
      access_token: "a",
      refresh_token: null,
    });
  });

  it("tolerates a leading hash or none", () => {
    expect(parseOAuthFragment("access_token=a")?.access_token).toBe("a");
  });

  it("returns null for an empty or token-less hash", () => {
    expect(parseOAuthFragment("")).toBeNull();
    expect(parseOAuthFragment("#error=state_invalid")).toBeNull();
    expect(parseOAuthFragment("#section")).toBeNull();
  });

  it("URL-decodes encoded token values", () => {
    expect(parseOAuthFragment("#access_token=a%2Fb%2Bc")?.access_token).toBe("a/b+c");
  });
});
