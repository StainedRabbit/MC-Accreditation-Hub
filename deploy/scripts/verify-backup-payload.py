"""Extract only the expected backup files and hash their extracted bytes.

No environment file is sourced and no database is accessed by this helper.
Checksums establish integrity, not archive authenticity.
"""

import hashlib
import re
import shutil
import sys
import tarfile
from pathlib import Path


LEGACY_PAYLOAD_FILES = frozenset(
    {"database.dump", "evidence.tar.gz", "environment.env", "manifest.txt", "SHA256SUMS"}
)
HASHED_FILES = frozenset({"database.dump", "evidence.tar.gz", "environment.env"})
PAYLOAD_FILES = LEGACY_PAYLOAD_FILES | {"schema.sql"}
HASHED_FILES_V2 = HASHED_FILES | {"schema.sql"}
PAYLOAD_NAME = re.compile(r"\.mc-hub-[0-9]{8}T[0-9]{6}Z(?:\.working|-[A-Za-z0-9]{8})")
CHECKSUM_ENTRY = re.compile(r"([0-9a-fA-F]{64}) [ *](database\.dump|evidence\.tar\.gz|environment\.env|schema\.sql)")


class VerificationError(ValueError):
    """An operator-safe failure message with no archive-supplied paths or data."""


def verify_payload(bundle: Path, restore_dir: Path) -> Path:
    """Require an existing empty private destination, never an existing payload."""
    if restore_dir.is_symlink() or not restore_dir.is_dir() or any(restore_dir.iterdir()):
        raise VerificationError("Restore destination must be an empty directory, not a link.")

    with tarfile.open(bundle, "r:gz") as archive:
        # Only six entries are valid. Bound metadata inspection as well as layout.
        members = []
        for member in archive:
            members.append(member)
            if len(members) > len(PAYLOAD_FILES) + 1:
                raise VerificationError("Backup has unexpected or duplicate archive entries.")
        roots = [member for member in members if member.isdir()]
        if len(roots) != 1 or not PAYLOAD_NAME.fullmatch(roots[0].name.rstrip("/")):
            raise VerificationError("Backup must contain exactly one expected payload directory.")
        root_name = roots[0].name.rstrip("/")
        files = {}
        for member in members:
            if member is roots[0]:
                continue
            prefix = root_name + "/"
            if not member.isfile() or not member.name.startswith(prefix):
                raise VerificationError("Backup contains an unsafe path, link or special entry.")
            name = member.name[len(prefix):]
            if name not in PAYLOAD_FILES or name in files:
                raise VerificationError("Backup contains an unexpected path or duplicate file.")
            files[name] = member
        if files.keys() not in (LEGACY_PAYLOAD_FILES, PAYLOAD_FILES):
            raise VerificationError("Backup is missing required payload files.")
        version_two = files.keys() == PAYLOAD_FILES
        if files["SHA256SUMS"].size > 1024:
            raise VerificationError("Checksum manifest is too large.")
        if files["manifest.txt"].size > 4096:
            raise VerificationError("Backup manifest is too large.")

        # Parse all entries before extraction or hashing. Never pass untrusted
        # manifest paths to a filesystem API or an external checksum checker.
        with archive.extractfile(files["SHA256SUMS"]) as manifest:
            lines = manifest.read().decode("ascii").removesuffix("\n").split("\n")
        expected = {}
        for line in lines:
            match = CHECKSUM_ENTRY.fullmatch(line)
            if not match or match[2] in expected:
                raise VerificationError("Unsafe or duplicate checksum entry; legacy absolute paths are not supported.")
            expected[match[2]] = match[1].lower()
        if expected.keys() != (HASHED_FILES_V2 if version_two else HASHED_FILES):
            raise VerificationError("Checksum manifest must cover every required hashed file exactly once.")

        if version_two:
            with archive.extractfile(files["manifest.txt"]) as source:
                try:
                    rows = source.read().decode("ascii").splitlines()
                except UnicodeDecodeError as error:
                    raise VerificationError("Backup manifest is invalid.") from error
            fields = {}
            for row in rows:
                if "=" not in row:
                    raise VerificationError("Backup manifest is invalid.")
                key, value = row.split("=", 1)
                if key in fields:
                    raise VerificationError("Backup manifest has duplicate fields.")
                fields[key] = value
            if (fields.keys() != {"format_version", "created_utc", "source_database", "release_commit", "schema_sha256"}
                    or fields["format_version"] != "2"
                    or not re.fullmatch(r"[0-9a-f]{40}", fields["release_commit"])
                    or not re.fullmatch(r"[0-9a-f]{64}", fields["schema_sha256"])
                    or fields["schema_sha256"] != expected["schema.sql"]):
                raise VerificationError("Backup release/schema manifest is invalid.")
            sidecar = Path(str(bundle) + ".sha256")
            try:
                with bundle.open("rb") as source:
                    actual = hashlib.file_digest(source, "sha256").hexdigest()
                recorded = sidecar.read_text(encoding="ascii")
            except (OSError, UnicodeError) as error:
                raise VerificationError("Backup archive sidecar is missing or invalid.") from error
            if recorded != f"{actual}  {bundle.name}\n":
                raise VerificationError("Backup archive sidecar does not match the bundle.")

        payload_dir = restore_dir / root_name
        payload_dir.mkdir(mode=0o700)
        for name, member in files.items():
            # Manual extraction avoids tar paths/links/ownership metadata. Names
            # come from the fixed allowlist; exclusive creation prevents reuse.
            with archive.extractfile(member) as source, (payload_dir / name).open("xb") as target:
                shutil.copyfileobj(source, target)
            (payload_dir / name).chmod(0o600)

    for name, checksum in expected.items():
        with (payload_dir / name).open("rb") as extracted_file:
            actual = hashlib.file_digest(extracted_file, "sha256").hexdigest()
        if actual != checksum:
            raise VerificationError("Extracted payload checksum mismatch: " + name)
    if version_two:
        seen = set()
        with tarfile.open(payload_dir / "evidence.tar.gz", "r:gz") as evidence:
            for member in evidence:
                parts = member.name.split("/")
                if (member.name.startswith("/") or ".." in parts or "" in parts[:-1]
                        or not (member.isfile() or member.isdir()) or member.name in seen):
                    raise VerificationError("Evidence archive contains an unsafe or duplicate entry.")
                seen.add(member.name)
    return payload_dir


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: verify-backup-payload.py BACKUP EMPTY_RESTORE_DIRECTORY", file=sys.stderr)
        return 1
    try:
        payload_dir = verify_payload(Path(sys.argv[1]), Path(sys.argv[2]))
    except VerificationError as error:
        print("Backup payload verification failed: " + str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError, EOFError, tarfile.TarError) as error:
        # Do not emit paths, environment contents or raw archive error details.
        print("Backup payload verification failed (" + type(error).__name__ + ").", file=sys.stderr)
        return 1
    print(payload_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
