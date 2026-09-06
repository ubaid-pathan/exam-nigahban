"""Evidence image storage abstraction (local filesystem or S3-compatible).

This module is the ONLY place that knows where evidence images live.
Routes and models never construct storage paths themselves -- they call
`save_evidence_image` / `read_evidence_image` / `delete_evidence_file` and
treat the returned/consumed value as an opaque relative path (which is the
object key when the s3 backend is active). Swapping storage backends never
touches model/route/schema code.

Backends (settings.evidence_backend):

* "local" -- writes under settings.evidence_storage_root. Fine for
  development, but the filesystem is ephemeral on hosts like Render, so the
  API route also keeps a base64 copy of the image in the DB row as a
  survival fallback (see `evidence_storage_is_durable`).
* "s3"   -- uploads to S3-compatible object storage (e.g. Cloudflare R2)
  and reads bytes back from there. Objects are durable across redeploys,
  so no DB fallback copy is kept.

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

# botocore error codes meaning "the object/bucket does not exist" rather
# than "the request failed". A missing object must surface as
# FileNotFoundError (an OSError) so the callers' existing missing-file
# fallback in the evidence routes keeps working for both backends.
_S3_MISSING_CODES = {"NoSuchKey", "NoSuchBucket", "404"}

_s3_client_cache = None


class EvidenceValidationError(ValueError):
    """Raised when a submitted evidence image fails validation.

    Callers (API routes) MUST treat this as evidence-only failure: the
    monitoring event itself must still be created successfully.
    """


def evidence_storage_is_durable() -> bool:
    """True when stored evidence survives a redeploy of the API host.

    Routes use this to decide whether to also keep a base64 fallback copy
    of the image in the database row -- only the ephemeral local backend
    needs that safety net.
    """
    return settings.evidence_backend == "s3"


def _storage_root() -> Path:
    configured = Path(settings.evidence_storage_root)
    if configured.is_absolute():
        return configured
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / configured


def _s3_client():
    """Lazily builds (and caches) the boto3 client for object storage.

    boto3 is imported lazily so the default local backend never pays its
    import cost or breaks on environments where it is not installed.
    """
    global _s3_client_cache
    if _s3_client_cache is None:
        try:
            import boto3
        except ImportError as exc:
            raise OSError(
                "EVIDENCE_BACKEND=s3 requires boto3 to be installed "
                "(pip install boto3)"
            ) from exc
        _s3_client_cache = boto3.client(
            "s3",
            endpoint_url=settings.evidence_s3_endpoint_url or None,
            region_name=settings.evidence_s3_region,
            aws_access_key_id=settings.evidence_s3_access_key_id,
            aws_secret_access_key=settings.evidence_s3_secret_access_key,
        )
    return _s3_client_cache


def _relative_key(event_id: int, captured_at: datetime) -> str:
    """YYYY/MM/DD/EVT-<event_id>.jpg, always with forward slashes.

    Forward slashes keep stored paths valid as S3 object keys and
    platform-independent in the database (Path handles them on Windows
    too), so the same layout serves both backends.
    """
    relative_dir = Path(f"{captured_at:%Y}") / f"{captured_at:%m}" / f"{captured_at:%d}"
    return (relative_dir / f"EVT-{event_id:06d}.jpg").as_posix()


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


def upload_evidence_object(image_bytes: bytes, key: str) -> None:
    """Stores raw image bytes at an explicit relative key (s3 backend).

    `save_evidence_image` derives the key itself; the one-time
    migrate_evidence_to_s3.py script uses this to place legacy images at
    the keys already recorded in their database rows.

    Raises OSError on failure so callers can treat any storage write
    problem uniformly across backends.
    """
    from botocore.exceptions import ClientError

    try:
        _s3_client().put_object(
            Bucket=settings.evidence_s3_bucket,
            Key=key,
            Body=image_bytes,
            ContentType="image/jpeg",
        )
    except ClientError as exc:
        raise OSError(f"Failed to store evidence object '{key}': {exc}") from exc


def save_evidence_image(image_bytes: bytes, event_id: int, captured_at: datetime) -> str:
    """Stores a validated JPEG as YYYY/MM/DD/EVT-<event_id>.jpg.

    Returns the path/key relative to the storage root (never an absolute
    filesystem path -- callers must not expose this value to API clients).
    """
    relative_key = _relative_key(event_id, captured_at)

    if settings.evidence_backend == "s3":
        upload_evidence_object(image_bytes, relative_key)
        return relative_key

    absolute_path = _storage_root() / relative_key
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(image_bytes)

    return relative_key


def read_evidence_image(relative_path: str) -> bytes:
    """Reads a stored evidence image.

    Raises FileNotFoundError (an OSError) when the image is missing, so
    callers can fall back uniformly for both backends.
    """
    if settings.evidence_backend == "s3":
        from botocore.exceptions import ClientError

        try:
            response = _s3_client().get_object(
                Bucket=settings.evidence_s3_bucket,
                Key=relative_path,
            )
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in _S3_MISSING_CODES:
                raise FileNotFoundError(
                    f"Evidence object '{relative_path}' not found"
                ) from exc
            raise OSError(
                f"Failed to read evidence object '{relative_path}': {exc}"
            ) from exc
        return response["Body"].read()

    return (_storage_root() / relative_path).read_bytes()


def delete_evidence_file(relative_path: str) -> None:
    """Best-effort cleanup for when a DB write fails after the image was
    already stored, so a failed commit never leaves an orphaned image."""
    if settings.evidence_backend == "s3":
        from botocore.exceptions import ClientError

        try:
            _s3_client().delete_object(
                Bucket=settings.evidence_s3_bucket,
                Key=relative_path,
            )
        except ClientError:
            pass
        return

    try:
        (_storage_root() / relative_path).unlink(missing_ok=True)
    except OSError:
        pass
