from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ExportCreateRequest(BaseModel):
    format: str = Field(default="xlsx", description="pdf or xlsx")


class ExportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    export_id: str
    boq_id: str
    format: str
    filename: str
    status: str = "completed"
    download_url: str
    generated_at: datetime
