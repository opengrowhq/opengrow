import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CHANNEL_PRESETS, buildBrief, generatedTitle } from "../presets.mjs";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

// Render the shell as a passthrough so we test the studio, not the nav.
vi.mock("@/components/ui/app-shell", () => ({
  AppShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/features/auth", () => ({
  useAuthGuard: () => true,
  useMe: () => ({ data: { tenant_slug: "demo" } }),
}));
let brands: { id: string }[] = [{ id: "b1" }];
vi.mock("@/features/brand", () => ({ useBrands: () => ({ data: brands }) }));

const saveMutate = vi.fn();
vi.mock("@/features/content", () => ({
  useCreateFromGeneration: () => ({ mutate: saveMutate, isPending: false }),
}));

const createMutate = vi.fn();
let generation: { status: string; result: string | null; error_message: string | null } | undefined;
vi.mock("../hooks", () => ({
  useUploadAsset: () => ({ mutate: vi.fn(), isPending: false }),
  useAsset: () => ({ data: undefined }),
  useCreateGeneration: () => ({ mutate: createMutate, isPending: false, error: null }),
  useGeneration: () => ({ data: generation }),
}));

import { GeneratorStudio } from "./generator-studio";

describe("GeneratorStudio (Ads preset)", () => {
  const preset = CHANNEL_PRESETS.ads;

  beforeEach(() => {
    push.mockClear();
    createMutate.mockReset();
    saveMutate.mockReset();
    generation = undefined;
    brands = [{ id: "b1" }];
  });

  it("frames the brief with the channel preset and calls the generation API", async () => {
    const user = userEvent.setup();
    render(<GeneratorStudio presetKey="ads" />);

    await user.type(screen.getByPlaceholderText(preset.placeholder), "Launch sale for founders");
    await user.click(screen.getByRole("button", { name: "Generate" }));

    expect(createMutate).toHaveBeenCalledTimes(1);
    expect(createMutate.mock.calls[0][0]).toEqual({
      brief: buildBrief(preset, "Launch sale for founders"),
      referenceAssetId: undefined,
    });
  });

  it("renders the result and saves it to the library with a channel-tagged title", async () => {
    // generation resolves to COMPLETE as soon as it's created
    generation = { status: "COMPLETE", result: "Ad copy here", error_message: null };
    createMutate.mockImplementation((_vars, opts) => opts.onSuccess({ id: "g1" }));
    const user = userEvent.setup();
    render(<GeneratorStudio presetKey="ads" />);

    await user.type(screen.getByPlaceholderText(preset.placeholder), "Launch sale");
    await user.click(screen.getByRole("button", { name: "Generate" }));

    expect(screen.getByText("Ad copy here")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /save to library/i }));
    expect(saveMutate).toHaveBeenCalledWith(
      { generationId: "g1", title: generatedTitle(preset, "Launch sale") },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it("prompts to set up a brand when none exists", () => {
    brands = [];
    render(<GeneratorStudio presetKey="socials" />);
    expect(screen.getByText(/add your brand first/i)).toBeInTheDocument();
  });
});
