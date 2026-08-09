import { apiGet, apiSend } from "@/lib/http";

export type BrandProfile = Record<string, unknown>;

export type Brand = {
  id: string;
  name: string;
  source_url: string | null;
  status: string;
  profile: BrandProfile | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export const listBrands = () => apiGet<Brand[]>("/brands");
export const getBrand = (id: string) => apiGet<Brand>(`/brands/${id}`);

export const createBrand = (body: { name: string; source_url?: string | null }) =>
  apiSend<Brand>("/brands", "POST", body);

export const updateBrand = (
  id: string,
  patch: { name?: string; profile?: BrandProfile },
) => apiSend<Brand>(`/brands/${id}`, "PATCH", patch);
