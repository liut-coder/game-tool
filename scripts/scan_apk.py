#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
from pathlib import Path


APK_SCAN_ROOT = Path("/root/tiandao_apk_scan")
APK_FILE = Path("/root/tiandao_zip_extracted/天道.apk")
OLD_IPS = [
    "106.55.60.178",
    "38.175.203.40",
    "27.25.159.141",
    "1.94.96.71",
    "103.85.85.176",
    "111.180.197.115",
    "49.235.187.128",
    "180.188.19.128",
    "111.231.68.61",
]
SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".mp3",
    ".mp4",
    ".so",
    ".dex",
    ".dat",
    ".bin",
    ".luac",
    ".bks",
    ".cer",
}
INCLUDE_SUFFIXES = {
    ".json",
    ".properties",
    ".xml",
    ".html",
    ".txt",
    ".plist",
}
PRUNE_DIRS = {
    "obb",
    "res",
    "src",
    "facetheme",
    "images",
    "icon",
    "ijm_lib",
}
MAX_FILES = 2500


def is_text(path: Path) -> bool:
    if path.suffix.lower() in SKIP_SUFFIXES:
        return False
    if path.suffix.lower() not in INCLUDE_SUFFIXES:
        return False
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\0" not in chunk


def scan_files() -> list[str]:
    if not APK_SCAN_ROOT.exists():
        return [f"[WARN] APK scan directory missing: {APK_SCAN_ROOT}"]
    hits: list[str] = []
    pattern = re.compile(r"https?://[^\s\"'<>]+|" + "|".join(re.escape(ip) for ip in OLD_IPS))
    scanned = 0
    for path in APK_SCAN_ROOT.rglob("*"):
        if any(part in PRUNE_DIRS for part in path.relative_to(APK_SCAN_ROOT).parts[:-1]):
            continue
        if not path.is_file() or not is_text(path):
            continue
        scanned += 1
        if scanned > MAX_FILES:
            hits.append(f"[WARN] scan stopped after {MAX_FILES} text files")
            break
        try:
            text = path.read_text(errors="ignore")
        except OSError:
            continue
        found = sorted(set(pattern.findall(text)))
        if found:
            rel = path.relative_to(APK_SCAN_ROOT)
            hits.append(f"{rel}:")
            for item in found[:20]:
                hits.append(f"  {item}")
    return hits


def main() -> int:
    print(f"APK: {APK_FILE} {'OK' if APK_FILE.exists() else 'MISSING'}")
    print(f"Unpacked scan dir: {APK_SCAN_ROOT} {'OK' if APK_SCAN_ROOT.exists() else 'MISSING'}")
    print()
    print("Tool availability:")
    for tool in ["apktool", "apksigner", "zipalign", "keytool", "jarsigner", "7z", "unzip"]:
        print(f"  {tool}: {shutil.which(tool) or '-'}")
    print()
    print("URL/IP hits in text-like APK files:")
    hits = scan_files()
    if hits:
        for line in hits[:240]:
            print(line)
        if len(hits) > 240:
            print(f"... truncated, {len(hits) - 240} more lines")
    else:
        print("  none")
    print()
    if not shutil.which("apktool") or not shutil.which("apksigner") or not shutil.which("zipalign"):
        print("[NEXT] Install apktool + Android build-tools before reliable rebuild/sign.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
