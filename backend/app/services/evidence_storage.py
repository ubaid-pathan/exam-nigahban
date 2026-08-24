"""Local-filesystem evidence storage abstraction.

This module is the ONLY place that knows evidence images live on disk.
Routes and models never construct filesystem paths themselves -- they call
`save_evidence_image` / `read_evidence_image` / `delete_evidence_file` and
treat the returned/consumed value as an opaque relative path. Swapping to
object storage later means reimplementing only this module.

No image-parsing dependency (e.g. Pillow) is used: validation is limited to
size and JPEG magic-byte checks, which is sufficient for a single
downsized still frame captured client-side and keeps the dependency
footprint minimal per the project's engineering constraints.
"""

import base64
import binascii
from datetime import datetime
from pathlib import Path

from app.core.config import settings

# A downsized single JPEG frame (see frontend/src/monitoring/constants.js
# EVIDENCE_CAPTURE_MAX_WIDTH_PX/EVIDENCE_JPEG_QUALITY) is expected to be a
# few tens of KB; 300 KB leaves generous headroom while still rejecting
# anything resembling a full-resolution image or abuse payload.
MAX_IMAGE_BYTES = 300_000
JPEG_MAGIC = b"\xff\xd8\xff"


class EvidenceValidationError(ValueError):
    """Raised when a submitted evidence image fails validation.

    Callers (API routes) MUST treat this as evidence-only failure: the
    monitoring event itself must still be created successfully.
    """


def _storage_root() -> Path:
    configured = Path(settings.evidence_storage_root)
    if configured.is_absolute():
        return configured
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / configured


def decode_and_validate_image(image_base64: str) -> bytes:
    """Decodes a base64-encoded JPEG and enforces size/type limits.

    Raises EvidenceValidationError on any problem; never raises for
    reasons unrelated to the image content itself.
    """
    try:
        image_bytes = base64.b64decode(image_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise EvidenceValidationError("Evidence image is not valid base64") from exc

    if not image_bytes:
        raise EvidenceValidationError("Evidence image is empty")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise EvidenceValidationError("Evidence image exceeds the maximum allowed size")

    if not image_bytes.startswith(JPEG_MAGIC):
        raise EvidenceValidationError("Evidence image must be a JPEG")

    return image_bytes


def save_evidence_image(image_bytes: bytes, event_id: int, captured_at: datetime) -> str:
    """Writes a validated JPEG to <root>/YYYY/MM/DD/EVT-<event_id>.jpg.

    Returns the path relative to the storage root (never an absolute
    filesystem path -- callers must not expose this value to API clients).
    """
    relative_dir = Path(f"{captured_at:%Y}") / f"{captured_at:%m}" / f"{captured_at:%d}"
    absolute_dir = _storage_root() / relative_dir
    absolute_dir.mkdir(parents=True, exist_ok=True)

    filename = f"EVT-{event_id:06d}.jpg"
    (absolute_dir / filename).write_bytes(image_bytes)

    return str(relative_dir / filename)


def delete_evidence_file(relative_path: str) -> None:
    """Best-effort cleanup for when a DB write fails after the file was
    already written, so a failed commit never leaves an orphaned file."""
    try:
        (_storage_root() / relative_path).unlink(missing_ok=True)
    except OSError:
        pass


def read_evidence_image(relative_path: str) -> bytes:
    return (_storage_root() / relative_path).read_bytes()
