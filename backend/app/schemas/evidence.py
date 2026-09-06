from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# The metadata key holding the ephemeral-filesystem fallback copy of the
# image. It belongs in the database row but must never be serialized into
# an API response -- see EvidenceResponse.strip_image_fallback below.
IMAGE_FALLBACK_KEY = "image_base64"


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

    @field_validator("metadata")
    @classmethod
    def strip_image_fallback(cls, value: dict) -> dict:
        """Removes the embedded base64 image from the serialized metadata.

        With EVIDENCE_BACKEND=local the row keeps a full base64 copy of the
        JPEG as a survival fallback for ephemeral filesystems (see
        app/api/routes/monitoring.py::_try_attach_evidence). That copy is
        needed in the DATABASE, but returning it in every evidence payload
        meant a listing of N rows carried N whole images inline -- tens of
        megabytes of JSON for a few hundred events.

        Callers that need the image use GET /api/evidence/{id}/image, which
        still falls back to this stored copy when the file is missing. The
        stored row is untouched; only the response drops the key.
        """
        if not value:
            return {}
        return {key: item for key, item in value.items() if key != IMAGE_FALLBACK_KEY}


class EvidenceListResponse(BaseModel):
    """Paginated evidence listing.

    GET /api/evidence was the only listing in the API returning an
    unbounded array; every other one (monitoring events, enforcement,
    audit, students, admins) is paginated. It now matches them.
    """

    items: list[EvidenceResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
