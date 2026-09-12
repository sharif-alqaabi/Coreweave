from pathlib import Path

from helix.kit import load_kit, promote, rollback, validate_diff
from helix.schema import KitDiff, KitPatch, PatchKind


def _seed(root: Path):
    for sub in ("rules", "skills", "tools"):
        (root / sub).mkdir(parents=True)
    (root / "VERSION").write_text("1")
    (root / "rules" / "000_base.md").write_text("no lead without trace")


def test_promote_and_rollback(tmp_path):
    _seed(tmp_path)
    kit = load_kit(tmp_path)
    diff = KitDiff(iteration=1, summary="s", patches=[
        KitPatch(kind=PatchKind.RULE, path="rules/001_new.md", content="new rule", rationale="r"),
    ])
    assert validate_diff(diff, kit) == []
    new = promote(diff, kit)
    assert new.version == "2"
    assert "001_new" in new.rules
    back = rollback(new, "1")
    assert back.version == "1"
    assert "001_new" not in back.rules


def test_validate_rejects_bad_paths(tmp_path):
    _seed(tmp_path)
    kit = load_kit(tmp_path)
    diff = KitDiff(iteration=1, summary="s", patches=[
        KitPatch(kind=PatchKind.RULE, path="../escape.md", content="x", rationale="r"),
        KitPatch(kind=PatchKind.SKILL, path="rules/wrong_dir.md", content="x", rationale="r"),
        KitPatch(kind=PatchKind.TOOL, path="tools/empty.py", content="  ", rationale="r"),
    ])
    problems = validate_diff(diff, kit)
    assert len(problems) == 3
