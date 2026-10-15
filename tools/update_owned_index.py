#!/usr/bin/env python3
import argparse
import gzip
import json
from pathlib import Path

from google.protobuf import json_format
import index_pb2


def normalize_fingerprint(value: str) -> str:
    return value.replace(":", "").replace(" ", "").strip().lower()


def load_or_new(
    path: Path,
    fingerprint: str,
    name: str,
    badge_label: str,
    website: str,
) -> index_pb2.Index:
    if path.exists():
        index = json_format.Parse(path.read_text(encoding="utf-8"), index_pb2.Index())
        index.name = name
        index.badgeLabel = badge_label
        index.signingKey = normalize_fingerprint(fingerprint)
        index.contact.website = website
        return index

    return index_pb2.Index(
        name=name,
        badgeLabel=badge_label,
        signingKey=normalize_fingerprint(fingerprint),
        contact=index_pb2.Contact(website=website),
        extensionList=index_pb2.ExtensionList(),
    )


def build_extension(info: dict, apk_url: str, jar_url: str, icon_url: str) -> index_pb2.Extension:
    sources = []
    for source in info.get("sources", []):
        sources.append(
            index_pb2.Source(
                id=int(source["id"]),
                name=source["name"],
                language=source["lang"],
                homeUrl=source["baseUrl"],
                mirrorUrls=source.get("mirrorUrls", []),
            )
        )

    resources = index_pb2.Resources(apkUrl=apk_url, iconUrl=icon_url)
    if jar_url:
        resources.jarUrl = jar_url

    return index_pb2.Extension(
        name=info["name"],
        packageName=info["packageName"],
        resources=resources,
        extensionLib=info["extensionLib"],
        versionCode=int(info["versionCode"]),
        versionName=info["versionName"],
        contentWarning=int(info.get("contentWarning", 0)),
        sources=sources,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--info", required=True)
    parser.add_argument("--apk-url", required=True)
    parser.add_argument("--jar-url", default="")
    parser.add_argument("--icon-url", required=True)
    parser.add_argument("--fingerprint", required=True)
    parser.add_argument("--output-dir", default="owned")
    parser.add_argument(
        "--index-url",
        default="https://raw.githubusercontent.com/xceella/madomi-bl-repo/main/owned/index.pb",
    )
    parser.add_argument("--name", default="Xceella BL Extensions")
    parser.add_argument("--badge-label", default="XBL")
    parser.add_argument(
        "--website",
        default="https://github.com/xceella/madomi-bl-repo",
    )
    args = parser.parse_args()

    info = json.loads(Path(args.info).read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    index_json = output_dir / "index.json"
    index = load_or_new(
        index_json,
        args.fingerprint,
        args.name,
        args.badge_label,
        args.website,
    )

    replacement = build_extension(info, args.apk_url, args.jar_url, args.icon_url)
    kept = [
        ext
        for ext in index.extensionList.extensions
        if ext.packageName != replacement.packageName
    ]
    kept.append(replacement)
    kept.sort(key=lambda ext: ext.packageName)

    index.extensionList.ClearField("extensions")
    index.extensionList.extensions.extend(kept)

    index_json.write_text(
        json_format.MessageToJson(
            index,
            preserving_proto_field_name=True,
            always_print_fields_with_no_presence=False,
        ),
        encoding="utf-8",
    )

    with (output_dir / "index.pb").open("wb") as handle:
        handle.write(gzip.compress(index.SerializeToString(deterministic=True), mtime=0))

    repo_json = {
        "index_v2": args.index_url,
        "meta": {
            "name": args.name,
            "website": args.website,
            "signingKeyFingerprint": normalize_fingerprint(args.fingerprint),
        },
    }
    (output_dir / "repo.json").write_text(
        json.dumps(repo_json, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Atualizado: {replacement.name} {replacement.versionName}")
    print(f"Extensões no índice: {len(kept)}")


if __name__ == "__main__":
    main()
