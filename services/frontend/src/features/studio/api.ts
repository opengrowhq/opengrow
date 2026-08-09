import { API_BASE, apiGet, apiSend, authHeaders, parse } from "@/lib/http";

export type Asset = {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: string;
  scan_message: string | null;
};

export type Generation = {
  id: string;
  status: string;
  brief: string;
  result: string | null;
  error_message: string | null;
  task_id: string | null;
};

export const getAsset = (id: string) => apiGet<Asset>(`/assets/${id}`);
export const getGeneration = (id: string) => apiGet<Generation>(`/generations/${id}`);

export const createGeneration = (brief: string, reference_asset_id?: string) =>
  apiSend<Generation>("/generations", "POST", { brief, reference_asset_id }); // model = backend default

export async function uploadAsset(file: File): Promise<{ asset_id: string }> {
  const form = new FormData();
  form.append("file", file);
  return parse(
    await fetch(`${API_BASE}/assets/upload`, {
      method: "POST",
      headers: authHeaders(), // no Content-Type — browser sets multipart boundary
      body: form,
    }),
  );
}
