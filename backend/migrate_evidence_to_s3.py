"""One-time migration: move DB-embedded evidence images to object storage.

Before durable object storage was introduced (EVIDENCE_BACKEND=s3), every
evidence row kept a base64 copy of its image inside the metadata JSON
column as a survival fallback for Render's ephemeral filesystem. With the
s3 backend active that copy is redundant -- new rows no longer embed it --
but legacy rows still bloat the database by roughly the full size of each
image on every row.

This migration, meant to be run ONCE in the deployed environment with
EVIDENCE_BACKEND=s3 configured:

  1. For every evidence row whose metadata still embeds image_base64:
     verifies the image object exists in the bucket under the row's
     image_path key, uploading the decoded fallback copy when it does not.
  2. Strips image_base64 from that row's metadata and commits the slimmed
     row, keeping content_type/size_bytes intact.

Idempotent: rows without an embedded base64 are skipped, and existing
objects are never overwritten (checked with head_object), so re-running
against a migrated database is a no-op. Each row is committed
individually, so an interrupted run can simply be re-run.

Usage (e.g. from the Render Shell, with the s3 environment variables set):
    python migrate_evidence_to_s3.py
"""

from __future__ import annotations

import base64
import binascii

from botocore.exceptions import ClientError

from app.core.config import settings
from app.db.models import Evidence
from app.db.session import SessionLocal
from app.services import evidence_storage


def _object_exists(key: str) -> bool:
    try:
        evidence_storage._s3_client().head_object(
            Bucket=settings.evidence_s3_bucket,
            Key=key,
        )
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in evidence_storage._S3_MISSING_CODES:
            return False
        raise


def main() -> int:
    if settings.evidence_backend != "s3":
        print(
            "EVIDENCE_BACKEND must be set to 's3' (with bucket and "
            "credentials) before running this migration. Aborting."
        )
        return 1

    # Build the client up front: bad credentials should abort the run
    # before any row is touched, not fail halfway through.
    evidence_storage._s3_client()

    uploaded = stripped = skipped = failed = 0
    moved_bytes = reclaimed_chars = 0

    with SessionLocal() as db:
        rows = db.query(Evidence).order_by(Evidence.id).all()
        print(f"Scanning {len(rows)} evidence row(s) for embedded images...")

        for row in rows:
            embedded = (row.metadata_json or {}).get("image_base64")
            if not embedded:
                skipped += 1
                continue

            key = row.image_path
            try:
                if not _object_exists(key):
                    image_bytes = base64.b64decode(embedded, validate=True)
                    if not image_bytes.startswith(evidence_storage.JPEG_MAGIC):
                        print(
                            f"  ! evidence {row.id}: embedded copy is not a "
                            "JPEG; leaving row untouched"
                        )
                        failed += 1
                        continue
                    evidence_storage.upload_evidence_object(image_bytes, key)
                    uploaded += 1
                    moved_bytes += len(image_bytes)
                    print(f"  uploaded evidence {row.id} -> '{key}'")

                metadata = dict(row.metadata_json or {})
                reclaimed_chars += len(metadata.pop("image_base64"))
                # Reassign (not mutate) so SQLAlchemy marks the JSON
                # column dirty and the slimmed metadata is persisted.
                row.metadata_json = metadata
                db.commit()
                stripped += 1
            except (OSError, ValueError, binascii.Error) as exc:
                db.rollback()
                failed += 1
                print(f"  ! evidence {row.id}: {exc}")

    print()
    print("Migration summary:")
    print(f"  rows scanned:      {len(rows)}")
    print(f"  objects uploaded:  {uploaded} ({moved_bytes} bytes)")
    print(f"  rows slimmed:      {stripped} (~{reclaimed_chars} base64 chars reclaimed)")
    print(f"  rows skipped:      {skipped} (no embedded image)")
    if failed:
        print(f"  rows FAILED:       {failed} (see messages above; re-run after fixing)")
        return 1
    print("Migration complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
