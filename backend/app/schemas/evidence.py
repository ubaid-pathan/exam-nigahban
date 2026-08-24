from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    captured_at: datetime
    # Aliased so the API surface uses "metadata" (matching the project
    # specification) while the Python/ORM attribute stays metadata_json to
    # avoid colliding with SQLAlchemy's reserved Base.metadata. Always
    # construct this model via model_validate(evidence_row) so the alias
    # is resolved from the ORM attribute correctly.
    metadata: dict = Field(validation_alias="metadata_json")

    # image_path is intentionally NOT exposed here -- raw filesystem paths
    # must never appear in an API response. Retrieve the actual image via
    # GET /api/evidence/{id}/image instead.
