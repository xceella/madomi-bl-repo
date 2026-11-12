#!/usr/bin/env python3
"""Choose only XBL extensions touched by a GitHub push or a manual build."""
import json
import os
import subprocess
from pathlib import Path


def main() -> None:
    catalog = json.loads(Path("catalog/sources.json").read_text(encoding="utf-8"))
    by_slug = {entry["slug"]: entry for entry in catalog}
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    before = os.environ.get("XBL_BEFORE", "")
    target = os.environ.get("XBL_MANUAL_SOURCE", "all").strip()
    selected = set()

    if event == "workflow_dispatch":
        if target == "all":
            selected = set(by_slug)
        elif target in by_slug:
            selected.add(target)
        else:
            raise SystemExit(f"::error::Fonte inválida para compilação manual: {target}")
    else:
        if not before or before == "0" * 40:
            # Initial push or a missing commit range: do not guess a partial diff.
            selected = set(by_slug)
        else:
            paths = subprocess.check_output(
                ["git", "diff", "--name-only", before, os.environ["GITHUB_SHA"]],
                text=True,
            ).splitlines()
            for path in paths:
                for entry in catalog:
                    custom = entry.get("custom")
                    if custom and (path == custom or path.startswith(custom + "/")):
                        selected.add(entry["slug"])
            if "catalog/sources.json" in paths:
                try:
                    previous_catalog = json.loads(
                        subprocess.check_output(
                            ["git", "show", f"{before}:catalog/sources.json"],
                            text=True,
                        )
                    )
                except subprocess.CalledProcessError:
                    selected = set(by_slug)
                else:
                    previous = {entry["slug"]: entry for entry in previous_catalog}
                    for slug, entry in by_slug.items():
                        if previous.get(slug) != entry:
                            selected.add(slug)
                    removed = set(previous) - set(by_slug)
                    if removed:
                        raise SystemExit(
                            "::error::Remoção do catálogo exige uma migração explícita: "
                            + ", ".join(sorted(removed))
                        )

    picked = [entry for entry in catalog if entry["slug"] in selected]
    Path("selected-sources.json").write_text(
        json.dumps(picked, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    changed = "true" if picked else "false"
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as handle:
        handle.write(f"changed={changed}\n")
        handle.write(f"count={len(picked)}\n")
    print("Extensões selecionadas:", ", ".join(entry["slug"] for entry in picked) or "nenhuma")
    print("As outras versões publicadas serão preservadas, sem novas atualizações.")


if __name__ == "__main__":
    main()
