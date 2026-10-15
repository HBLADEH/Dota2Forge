"""Load only reviewed markdown from the built wheel with the actual host Skill parser."""

import json
import tempfile
from pathlib import Path
from zipfile import ZipFile

from pydantic_ai_skills import SkillsToolset

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PREFIX = "dota2forge_core/infrastructure/review_skills/"
REQUIRED = (
    "SKILL.md",
    "THIRD_PARTY_LICENSE.txt",
    "references/overview.md",
    "references/economy.md",
    "references/items.md",
    "references/team.md",
)


def main():
    with tempfile.TemporaryDirectory(prefix="dota2forge-skill-wheel-") as directory:
        root = Path(directory)
        with ZipFile(ROOT / "dist/dota2forge_core-0.1.0a9-py3-none-any.whl") as archive:
            for resource in REQUIRED:
                relative = "dota2-review/" + resource
                target = root / relative
                assert target.resolve().is_relative_to(root)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(PREFIX + relative))
        skills = SkillsToolset(directories=[root])
        skill = skills.get_skill("dota2-review")
        assert skill.metadata["metadata"]["version"] == "1.0.0"
        assert "STRATZ" in skill.content and not skill.scripts
        assert len(skill.resources) >= 4
        assert "TimZhang" in (root / "dota2-review/THIRD_PARTY_LICENSE.txt").read_text("utf-8")
        report = {
            "wheel_resources_verified": len(REQUIRED),
            "native_parser_loaded": True,
            "skill_version": "1.0.0",
            "executable_scripts": len(skill.scripts),
            "real_model": False,
            "real_platform_sends": False,
        }
    (HERE / "wheel-skill.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
