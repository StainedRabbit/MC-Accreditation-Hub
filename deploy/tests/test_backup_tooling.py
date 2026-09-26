"""Isolated backup regressions: synthetic files and stubbed external services only.

Run from the repository root: python -B -m unittest discover -s deploy/tests -v
Set BACKUP_TEST_BASH if Bash is not on PATH (e.g. Git Bash on Windows).
"""

import hashlib
import importlib.util
import io
import os
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "deploy" / "scripts"
spec = importlib.util.spec_from_file_location("backup_payload", SCRIPTS / "verify-backup-payload.py")
payload = importlib.util.module_from_spec(spec)
spec.loader.exec_module(payload)
gate_spec = importlib.util.spec_from_file_location("release_gate", SCRIPTS / "release-gate.py")
release_gate = importlib.util.module_from_spec(gate_spec)
gate_spec.loader.exec_module(release_gate)
ROOT_NAME = ".mc-hub-20260917T000000Z.working"
BASH = os.environ.get("BACKUP_TEST_BASH") or shutil.which("bash")


def shell_path(path):
    value = Path(path).resolve().as_posix()
    if os.name == "nt":
        return "/" + value[0].lower() + value[2:]
    return value


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mc-hub-backup-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.files = {
            "database.dump": b"synthetic dump, not a real database",
            "evidence.tar.gz": b"synthetic evidence",
            "environment.env": b"SYNTHETIC_ONLY=1\n",
            "manifest.txt": b"created_utc=2026-09-17T00:00:00Z\n",
        }
        self.files["SHA256SUMS"] = self.checksums()

    def checksums(self):
        return "".join(
            hashlib.sha256(self.files[name]).hexdigest() + "  " + name + "\n"
            for name in sorted(payload.HASHED_FILES)
        ).encode("ascii")

    def archive(self, extra=None, omitted=(), root=ROOT_NAME, link=None, link_type=tarfile.SYMTYPE):
        bundle = self.base / "copied-backup.tar.gz"
        with tarfile.open(bundle, "w:gz") as archive:
            directory = tarfile.TarInfo(root)
            directory.type = tarfile.DIRTYPE
            archive.addfile(directory)
            for name, data in self.files.items():
                if name in omitted:
                    continue
                member = tarfile.TarInfo(root + "/" + name)
                member.size = len(data)
                if name == link:
                    member.type = link_type
                    member.linkname = str(self.base / "source-host-file")
                    member.size = 0
                    archive.addfile(member)
                else:
                    archive.addfile(member, io.BytesIO(data))
            if extra is not None:
                member = tarfile.TarInfo(extra)
                member.size = 4
                archive.addfile(member, io.BytesIO(b"evil"))
        destination = self.base / "different-host" / "restore"
        destination.mkdir(parents=True)
        return bundle, destination

    def v2_archive(self, unsafe_evidence=False):
        self.files['schema.sql'] = b'CREATE TABLE synthetic_only (id integer);\n'
        evidence_bytes = io.BytesIO()
        with tarfile.open(fileobj=evidence_bytes, mode='w:gz') as evidence:
            item = tarfile.TarInfo('./fictional.txt')
            item.size = 9
            if unsafe_evidence:
                item.type = tarfile.SYMTYPE
                item.linkname = '/outside'
                item.size = 0
                evidence.addfile(item)
            else:
                evidence.addfile(item, io.BytesIO(b'fictional'))
        self.files['evidence.tar.gz'] = evidence_bytes.getvalue()
        schema_hash = hashlib.sha256(self.files['schema.sql']).hexdigest()
        self.files['manifest.txt'] = (
            'format_version=2\ncreated_utc=2026-09-17T00:00:00Z\n'
            'source_database=synthetic\nrelease_commit=' + 'a' * 40 +
            '\nschema_sha256=' + schema_hash + '\n').encode('ascii')
        self.files['SHA256SUMS'] = ''.join(
            hashlib.sha256(self.files[name]).hexdigest() + '  ' + name + '\n'
            for name in sorted(payload.HASHED_FILES_V2)).encode('ascii')
        bundle, destination = self.archive(root='.mc-hub-20260917T000000Z-ABCDEFGH')
        Path(str(bundle) + '.sha256').write_text(
            hashlib.sha256(bundle.read_bytes()).hexdigest() + '  ' + bundle.name + '\n', encoding='ascii')
        return bundle, destination

    def test_portable_payload_and_restrictive_permissions(self):
        result = payload.verify_payload(*self.archive())
        self.assertEqual(result.parent, self.base / "different-host" / "restore")
        for name, data in self.files.items():
            self.assertEqual((result / name).read_bytes(), data)
            if os.name != "nt":
                self.assertEqual((result / name).stat().st_mode & 0o777, 0o600)
        if os.name != "nt":
            self.assertEqual(result.stat().st_mode & 0o777, 0o700)

    def test_tampered_extracted_files_fail_even_with_intact_source_files(self):
        for name in sorted(payload.HASHED_FILES):
            with self.subTest(file=name), tempfile.TemporaryDirectory(dir=self.base) as scratch:
                original = self.files[name]
                (Path(scratch) / name).write_bytes(original)
                self.files[name] = original + b"tampered"
                bundle, destination = self.archive()
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    payload.verify_payload(bundle, destination)
                shutil.rmtree(destination)
                self.files[name] = original

    def test_unsafe_checksum_paths_fail_before_extraction(self):
        sentinel = self.base / "source-host-file"
        sentinel.write_bytes(b"original source bytes")
        digest = hashlib.sha256(sentinel.read_bytes()).hexdigest()
        unsafe = [str(sentinel), "/tmp/source-host-file", "../source-host-file",
                  "sub/../../source-host-file", "./database.dump", "sub/database.dump",
                  "C:\\source-host-file", "..\\source-host-file", "-", "database.dump\r"]
        for name in unsafe:
            with self.subTest(path=name):
                self.files["SHA256SUMS"] = (digest + "  " + name + "\n").encode("ascii")
                bundle, destination = self.archive()
                with self.assertRaisesRegex(ValueError, "checksum entry"):
                    payload.verify_payload(bundle, destination)
                self.assertEqual(list(destination.iterdir()), [])
                destination.rmdir()
                self.assertEqual(sentinel.read_bytes(), b"original source bytes")

    def test_duplicate_missing_malformed_and_oversized_checksums_fail(self):
        good = self.checksums()
        cases = [good + good.splitlines(keepends=True)[0], good.splitlines(keepends=True)[0],
                 good.replace(b"  database.dump", b"  unexpected.txt"), b"invalid\n",
                 b"x" * 1025, b"\xff\n", good + b"\n"]
        for manifest in cases:
            with self.subTest(manifest_length=len(manifest)):
                self.files["SHA256SUMS"] = manifest
                bundle, destination = self.archive()
                with self.assertRaises(ValueError):
                    payload.verify_payload(bundle, destination)
                self.assertEqual(list(destination.iterdir()), [])
                destination.rmdir()

    def test_missing_payload_files_fail(self):
        for name in payload.LEGACY_PAYLOAD_FILES:
            with self.subTest(file=name):
                bundle, destination = self.archive(omitted=[name])
                with self.assertRaisesRegex(ValueError, "missing"):
                    payload.verify_payload(bundle, destination)
                destination.rmdir()

    def test_archive_paths_duplicates_extra_roots_and_links_fail(self):
        for extra in ["/tmp/escaped", "../escaped", ROOT_NAME + "/../escaped",
                      ROOT_NAME + "/database.dump", "other-root/file"]:
            with self.subTest(path=extra):
                bundle, destination = self.archive(extra=extra)
                with self.assertRaises(ValueError):
                    payload.verify_payload(bundle, destination)
                self.assertEqual(list(destination.iterdir()), [])
                destination.rmdir()
        for options in [{"root": "../unsafe"}, {"link": "database.dump"},
                        {"link": "database.dump", "link_type": tarfile.LNKTYPE},
                        {"link": "database.dump", "link_type": tarfile.FIFOTYPE}]:
            bundle, destination = self.archive(**options)
            with self.assertRaises(ValueError):
                payload.verify_payload(bundle, destination)
            self.assertEqual(list(destination.iterdir()), [])
            destination.rmdir()

    def test_existing_nonempty_destination_is_untouched(self):
        bundle, destination = self.archive()
        sentinel = destination / "keep"
        sentinel.write_bytes(b"keep")
        with self.assertRaises(ValueError):
            payload.verify_payload(bundle, destination)
        self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_corrupt_archive_fails(self):
        bundle, destination = self.archive()
        bundle.write_bytes(b"not an archive")
        with self.assertRaises(tarfile.TarError):
            payload.verify_payload(bundle, destination)

    def test_v2_release_schema_sidecar_and_evidence_archive(self):
        bundle, destination = self.v2_archive()
        verified = payload.verify_payload(bundle, destination)
        self.assertEqual((verified / 'schema.sql').read_bytes(), self.files['schema.sql'])
        shutil.rmtree(destination)
        destination.mkdir()
        Path(str(bundle) + '.sha256').unlink()
        with self.assertRaisesRegex(ValueError, 'sidecar'):
            payload.verify_payload(bundle, destination)
        self.assertEqual(list(destination.iterdir()), [])

    def test_v2_unsafe_evidence_member_is_rejected(self):
        bundle, destination = self.v2_archive(unsafe_evidence=True)
        with self.assertRaisesRegex(ValueError, 'Evidence archive'):
            payload.verify_payload(bundle, destination)


class ReleaseGateTests(unittest.TestCase):
    def test_warnings_require_explicit_acceptance_and_errors_always_fail(self):
        class Message:
            def __init__(self, level, identifier):
                self.level, self.id, self.msg = level, identifier, "synthetic deployment check"
        warning = Message(30, "security.W021")
        error = Message(40, "security.E001")
        self.assertFalse(release_gate.evaluate_messages([warning], set(), ""))
        self.assertFalse(release_gate.evaluate_messages([warning], {warning.id}, ""))
        self.assertTrue(release_gate.evaluate_messages([warning], {warning.id}, "recorded test reason"))
        self.assertFalse(release_gate.evaluate_messages([error], {error.id}, "recorded test reason"))

    def test_pending_migrations_are_identified_for_a_failing_gate(self):
        class Migration:
            app_label = 'hub'
            name = '0008_synthetic'
        self.assertEqual(release_gate.pending_labels([(Migration(), False)]), ['hub.0008_synthetic'])


@unittest.skipUnless(BASH, "Bash required for isolated shell integration")
class ShellTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mc-hub-shell-test-", dir=REPO / "deploy" / "tests")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.env = os.environ.copy()
        # Replace inherited deployment settings. No real env file is opened.
        for name in ["MC_ENV_FILE", "BACKUP_ROOT", "PRIVATE_MEDIA_ROOT", "PGDATABASE",
                     "PGUSER", "PGPASSWORD", "PGHOST", "PGPORT", "VIRTUAL_ENV"]:
            self.env.pop(name, None)
        self.env["PATH"] = str(self.bin) + os.pathsep + self.env["PATH"]
        self.env["FIXTURE_ROOT"] = shell_path(self.base)
        self.env["FIXTURE_PYTHON"] = shell_path(sys.executable)
        self.env["MC_RELEASE_COMMIT"] = "a" * 40
        self.stub("pg_dump", 'for arg in "$@"; do case "$arg" in --file=*) printf synthetic-dump > "${arg#--file=}";; esac; done; if [[ "${FIXTURE_FAIL_DUMP:-0}" == 1 ]]; then exit 77; fi')
        self.stub("pg_restore", 'test "$#" = 2 && test "$1" = --list && test -f "$2"; printf list-only >> "$FIXTURE_ROOT/pg-restore-called"')
        self.stub("npm", 'printf "npm %s\\n" "$*" >> "$FIXTURE_ROOT/release-calls"')
        self.stub("curl", 'printf \'{"status":"ok"}\'')
        if os.name == "nt":
            self.stub("python3", 'output=$("$FIXTURE_PYTHON" "$(cygpath -w "$1")" "$(cygpath -w "$2")" "$(cygpath -w "$3")") || exit "$?"; cygpath -u "$output"')
        else:
            self.stub("python3", 'exec "$FIXTURE_PYTHON" "$@"')
        media = self.base / "synthetic-media"
        media.mkdir()
        (media / "fictional.txt").write_bytes(b"fictional evidence only")
        self.config = self.base / "synthetic.env"
        self.config.write_text(
            "BACKUP_ROOT=" + shlex.quote(shell_path(self.base / "backups")) + "\n"
            "PRIVATE_MEDIA_ROOT=" + shlex.quote(shell_path(media)) + "\n"
            "PGDATABASE=synthetic_never_connected\nDJANGO_ALLOWED_HOSTS=synthetic.invalid\n",
            encoding="utf-8",
        )
        self.env["MC_ENV_FILE"] = shell_path(self.config)

    def stub(self, name, body):
        file = self.bin / name
        file.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body + "\n", encoding="ascii", newline="\n")
        file.chmod(0o700)

    def run_shell(self, command, *args, success=True):
        script = ('set -euo pipefail\nexport PATH="$FIXTURE_ROOT/bin:/usr/bin:/bin"\nset -- '
                  + " ".join(shlex.quote(str(arg)) for arg in args) + "\n" + command + "\n")
        result = subprocess.run([BASH], input=script, env=self.env,
                                capture_output=True, text=True, timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_all_scripts_have_lf_syntax_and_executable_git_mode(self):
        for name in ["backup.sh", "restore-verify.sh", "release-check.sh"]:
            with self.subTest(script=name):
                self.assertNotIn(b"\r", (SCRIPTS / name).read_bytes())
                self.run_shell('bash -n "$1"', shell_path(SCRIPTS / name))
                mode = subprocess.check_output(
                    ["git", "ls-files", "--stage", "--", "deploy/scripts/" + name], cwd=REPO, text=True)
                self.assertTrue(mode.startswith("100755 "), mode)

    def test_direct_backup_copy_and_restore_without_source_paths(self):
        self.run_shell('"$1"', shell_path(SCRIPTS / "backup.sh"))
        backup_root = self.base / "backups"
        bundle = next(backup_root.glob("*.tar.gz"))
        self.assertEqual(list(backup_root.glob("*.working")), [])
        copied = self.base / "another-host"
        copied.mkdir()
        moved_bundle = copied / bundle.name
        shutil.copyfile(bundle, moved_bundle)
        shutil.copyfile(Path(str(bundle) + ".sha256"), Path(str(moved_bundle) + ".sha256"))
        shutil.rmtree(backup_root)
        self.run_shell('cd "$1" && sha256sum --check "$2"', shell_path(copied), bundle.name + ".sha256")
        destination = copied / "restored"
        self.run_shell('"$1" "$2" "$3"', shell_path(SCRIPTS / "restore-verify.sh"),
                       shell_path(moved_bundle), shell_path(destination))
        result = next(destination.iterdir())
        self.assertEqual((result / "database.dump").read_bytes(), b"synthetic-dump")
        self.assertEqual((result / "environment.env").read_bytes(), self.config.read_bytes())
        entries = (result / "SHA256SUMS").read_text().splitlines()
        self.assertEqual({line[66:] for line in entries}, payload.HASHED_FILES_V2)
        self.assertEqual((self.base / "pg-restore-called").read_text(), "list-only")
        manifest = dict(line.split("=", 1) for line in (result / "manifest.txt").read_text().splitlines())
        self.assertEqual(manifest['format_version'], '2')
        self.assertEqual(manifest['release_commit'], 'a' * 40)
        self.assertEqual(manifest['schema_sha256'], hashlib.sha256((result / 'schema.sql').read_bytes()).hexdigest())

    def test_overlapping_backup_and_interrupted_dump_publish_nothing(self):
        backup_root = self.base / 'backups'
        backup_root.mkdir()
        lock = backup_root / '.backup.lock'
        lock.mkdir()
        self.run_shell('"$1"', shell_path(SCRIPTS / 'backup.sh'), success=False)
        self.assertTrue(lock.is_dir())
        self.assertEqual(list(backup_root.glob('*.tar.gz')), [])
        lock.rmdir()
        self.env['FIXTURE_FAIL_DUMP'] = '1'
        self.run_shell('"$1"', shell_path(SCRIPTS / 'backup.sh'), success=False)
        self.assertFalse(lock.exists())
        self.assertEqual(list(backup_root.iterdir()), [])
        self.env.pop('FIXTURE_FAIL_DUMP')

    def test_failed_verification_cleans_new_destination_and_never_calls_pg_restore(self):
        bundle = self.base / "broken.tar.gz"
        bundle.write_bytes(b"synthetic invalid archive")
        destination = self.base / "failed-restore"
        self.run_shell('"$1" "$2" "$3"', shell_path(SCRIPTS / "restore-verify.sh"),
                       shell_path(bundle), shell_path(destination), success=False)
        self.assertFalse(destination.exists())
        self.assertFalse((self.base / "pg-restore-called").exists())

    def test_existing_destination_is_preserved(self):
        bundle = self.base / "broken.tar.gz"
        bundle.write_bytes(b"synthetic invalid archive")
        destination = self.base / "existing"
        destination.mkdir()
        sentinel = destination / "keep"
        sentinel.write_bytes(b"keep")
        self.run_shell('"$1" "$2" "$3"', shell_path(SCRIPTS / "restore-verify.sh"),
                       shell_path(bundle), shell_path(destination), success=False)
        self.assertEqual(sentinel.read_bytes(), b"keep")

    def test_release_checker_direct_invocation_with_stubbed_services(self):
        app = self.base / "synthetic-app"
        (app / "frontend").mkdir(parents=True)
        (self.base / "venv" / "bin").mkdir(parents=True)
        self.stub("python", 'printf "python %s\\n" "$*" >> "$FIXTURE_ROOT/release-calls"')
        shutil.copyfile(self.bin / "python", self.base / "venv" / "bin" / "python")
        (self.base / "venv" / "bin" / "python").chmod(0o700)
        self.env["VIRTUAL_ENV"] = shell_path(self.base / "venv")
        self.run_shell('"$1" "$2"', shell_path(SCRIPTS / "release-check.sh"), shell_path(app))
        self.assertEqual((self.base / "release-calls").read_text().splitlines(),
                         ["python deploy/scripts/release-gate.py " + shell_path(app),
                          "npm ci", "npm run build"])

    def test_release_checker_stops_when_gate_fails(self):
        app = self.base / 'synthetic-app'
        app.mkdir()
        (self.base / 'venv' / 'bin').mkdir(parents=True)
        self.stub('python', 'echo "unaccepted warning or pending migration" >&2; exit 1')
        shutil.copyfile(self.bin / 'python', self.base / 'venv' / 'bin' / 'python')
        (self.base / 'venv' / 'bin' / 'python').chmod(0o700)
        self.env['VIRTUAL_ENV'] = shell_path(self.base / 'venv')
        self.run_shell('"$1" "$2"', shell_path(SCRIPTS / 'release-check.sh'), shell_path(app), success=False)
        self.assertFalse((self.base / 'release-calls').exists())


if __name__ == "__main__":
    unittest.main()
