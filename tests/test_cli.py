import json
import io
from contextlib import redirect_stdout

from iris import cli, exit_codes


def run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.main(argv)
    return code, json.loads(buf.getvalue())


def test_version():
    code, out = run(["version"])
    assert code == exit_codes.OK and out["ok"] and "vocabulary" in out


def test_lexicon_term_and_unknown():
    code, out = run(["lexicon", "camera.movement.dolly_in"])
    assert code == exit_codes.OK and out["id"] == "dolly_in"
    code, out = run(["lexicon", "camera.movement.flying_saucer"])
    assert code == exit_codes.VALIDATION and out["ok"] is False and out["code"] == "validation"


def test_query_on_an_empty_workspace_returns_nothing(tmp_path):
    code, out = run(["query", "--term", "camera.movement.dolly_in", "--workspace", str(tmp_path)])
    assert code == exit_codes.OK and out["claims_total"] == 0


def test_analyze_unknown_asset_is_usage_error():
    code, out = run(["analyze", "ref_doesnotexist"])
    assert code == exit_codes.USAGE and out["ok"] is False


def test_doctor_emits_checks():
    code, out = run(["doctor"])
    assert "checks" in out and any(c["check"] == "registry" for c in out["checks"])
    assert code in (exit_codes.OK, exit_codes.VALIDATION)
