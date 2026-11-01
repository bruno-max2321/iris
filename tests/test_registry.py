import json
import subprocess
import sys

from iris import paths, registry


def test_vocabulary_loads_and_has_expected_shape():
    vocab = registry.load_vocabulary()
    assert vocab["language"] == "en"
    assert len(vocab["dimensions"]) >= 30
    assert sum(len(d["terms"]) for d in vocab["dimensions"]) >= 180


def test_every_iris_technique_resolves_bare():
    for tid in registry.term_ids("composition"):
        assert registry.resolve(tid) is not None, tid


def test_qualified_and_equals_forms_resolve():
    assert registry.resolve("camera.movement.dolly_in") == registry.resolve("camera.movement=dolly_in")
    assert registry.resolve("camera.movement.not_a_term") is None


def test_lexicon_card_fields():
    card = registry.lexicon_card("light.key.high_key")
    assert card and card["kind"] == "term"
    for key in ("definition", "observable_cues", "measurement_hints", "counterexamples", "claim_kind_default"):
        assert key in card, key


def test_dimension_summary():
    card = registry.lexicon_card("light.side")
    assert card and card["kind"] == "dimension"
    assert "key_screen_left" in card["terms"]


def test_vocabulary_validator_passes():
    validator = paths.REGISTRY_DIR / "tools" / "validate_vocabulary.py"
    p = subprocess.run([sys.executable, str(validator)], capture_output=True, text=True)
    assert p.returncode == 0, p.stdout[-800:] + p.stderr[-800:]


def test_no_spanish_in_registry_and_schemas():
    bad = []
    for root in (paths.REGISTRY_DIR, paths.SCHEMAS_DIR):
        for f in root.rglob("*"):
            if f.suffix in {".yaml", ".json", ".md", ".py"} and "capabilities" not in f.parts:
                text = f.read_text(encoding="utf-8", errors="ignore")
                if any(ch in text for ch in "áéíóúñ¿¡"):
                    bad.append(str(f.relative_to(paths.REPO_ROOT)))
    assert not bad, bad


def test_style_bible_example_validates_and_resolves_terms():
    import jsonschema

    schema = json.loads(paths.STYLE_BIBLE_SCHEMA.read_text(encoding="utf-8"))
    example = json.loads(paths.STYLE_BIBLE_EXAMPLE.read_text(encoding="utf-8"))
    assert not list(jsonschema.Draft202012Validator(schema).iter_errors(example))

    import re

    refs = []

    def walk(o, path=()):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, path + (k,))
        elif isinstance(o, list):
            for v in o:
                walk(v, path)
        elif isinstance(o, str) and re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", o) and "metric" not in path:
            refs.append(o)

    walk(example)
    unresolved = [r for r in refs if registry.resolve(r) is None]
    assert not unresolved, unresolved
