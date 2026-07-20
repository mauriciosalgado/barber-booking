"""The shop's logo, stored in the database so it survives restarts.

Keeping the logo here (rather than baked into the frontend image or a shared
volume) means the owner can replace it live from the UI — no redeploy, no
PersistentVolume — and every replica serves the same picture. The rows are
tiny, so the cost is negligible.
"""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class BrandAsset(SQLModel, table=True):
    key: str = Field(primary_key=True)  # e.g. "logo"
    content_type: str
    data: bytes
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def __str__(self) -> str:
        return f"{self.key} ({self.content_type})"
