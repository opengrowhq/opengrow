from pydantic import BaseModel


class AssetOut(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    status: str
    scan_message: str | None = None


class UploadResponse(BaseModel):
    asset_id: str
    scan_job_id: str
    status: str
