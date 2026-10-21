#!/usr/bin/env python3
"""
ksl_tool.py — Create, manage, and inspect .ksl (KSLearn Package) files

.k sl files are simple packages: a binary header + plain JSON payload.
No encryption. Author credentials are embedded in the header for credibility.

Usage:
    python ksl_tool.py                       # Interactive mode
    python ksl_tool.py info some_file.ksl     # Show file info
    python ksl_tool.py unpack some_file.ksl   # Extract to JSON
"""

import argparse
import json
import struct
import sys
from pathlib import Path
from datetime import datetime

# ─── Format Constants ───────────────────────────────────────────────
KSL_MAGIC = b"KSL\x01"
HEADER_SIZE = 128

# Author credential — not required; left blank for open packages
AUTHOR_CRED = b"\x00" * 36

# ─── Content Types ──────────────────────────────────────────────────
TYPE_NOTES = "notes"
TYPE_QUIZ = "quiz"
TYPE_FLASHCARD = "flashcard"
TYPE_TUTORIAL = "tutorial"
TYPE_BRAIN = "brain"
TYPE_COMBINED = "combined"

# ─── Default Output Directory ───────────────────────────────────────
def _get_ksl_dir():
    return Path(__file__).parent / "data" / "ksl"

def _ensure_ksl_dir():
    d = _get_ksl_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


# ═══════════════════════════════════════════════════════════════════
#  .ksl Binary Header
# ═══════════════════════════════════════════════════════════════════
#
#  Offset  Size      Description
#  ─────────────────────────────────────────────────────────────────
#  0       4 bytes   Magic: b"KSL\x01"
#  4       4 bytes   Header version (uint32 big-endian) = 1
#  8       16 bytes  Content type (null-padded string)
#  24      32 bytes  Title (null-padded string)
#  56      16 bytes  Author display name (null-padded string)
#  72      8 bytes   Created timestamp (uint64 big-endian, unix epoch)
#  80      8 bytes   Payload length (uint64 big-endian)
#  88      36 bytes  Author credential (provenance marker)
#  124     4 bytes   Content count (uint32 big-endian)
#
#  After header:
#  - Plain JSON payload (NOT encrypted)
#


def _pack_string(s: str, length: int) -> bytes:
    encoded = s.encode("utf-8")[:length]
    return encoded.ljust(length, b"\x00")


def _unpack_string(data: bytes) -> str:
    return data.split(b"\x00")[0].decode("utf-8", errors="replace").strip()


def _build_header(content_type: str, title: str, author: str,
                   payload_len: int, content_count: int) -> bytes:
    """Build the 128-byte KSL header with author credential."""
    header = bytearray(HEADER_SIZE)
    header[0:4] = KSL_MAGIC
    struct.pack_into(">I", header, 4, 1)                        # version
    header[8:24] = _pack_string(content_type, 16)               # type
    header[24:56] = _pack_string(title, 32)                     # title
    header[56:72] = _pack_string(author, 16)                    # author name
    struct.pack_into(">Q", header, 72, int(datetime.now().timestamp()))  # created
    struct.pack_into(">Q", header, 80, payload_len)             # payload length
    header[88:124] = AUTHOR_CRED                                # author credential
    struct.pack_into(">I", header, 124, content_count)          # content count
    return bytes(header)


def _parse_header(header: bytes) -> dict:
    """Parse the 128-byte KSL header."""
    if len(header) < HEADER_SIZE or header[0:4] != KSL_MAGIC:
        return None
    author_cred = _unpack_string(header[88:124])
    return {
        "version": struct.unpack_from(">I", header, 4)[0],
        "type": _unpack_string(header[8:24]),
        "title": _unpack_string(header[24:56]),
        "author": _unpack_string(header[56:72]),
        "created": datetime.fromtimestamp(
            struct.unpack_from(">Q", header, 72)[0]
        ).strftime("%Y-%m-%d %H:%M:%S"),
        "payload_length": struct.unpack_from(">Q", header, 80)[0],
        "content_count": struct.unpack_from(">I", header, 124)[0],
        "author_cred": author_cred,
    }


# ═══════════════════════════════════════════════════════════════════
#  Detect content type from JSON
# ═══════════════════════════════════════════════════════════════════

def detect_content_type(data: dict) -> str:
    types_found = set()
    if "notes" in data:
        if data["notes"] and "content" in str(data["notes"][0]):
            types_found.add(TYPE_NOTES)
    if "quiz_topics" in data:
        types_found.add(TYPE_QUIZ)
    if "flashcards" in data:
        types_found.add(TYPE_FLASHCARD)
    if "tutorials" in data:
        types_found.add(TYPE_TUTORIAL)
    if "brain_qa" in data:
        types_found.add(TYPE_BRAIN)
    if len(types_found) > 1:
        return TYPE_COMBINED
    return types_found.pop() if types_found else TYPE_NOTES


# ═══════════════════════════════════════════════════════════════════
#  Pack — JSON → .ksl
# ═══════════════════════════════════════════════════════════════════

def pack_ksl(input_files: list, output_path: Path = None, title: str = None,
             author: str = "kslearn", content_type: str = None) -> dict:
    """Pack one or more JSON files into .ksl.
    If output_path is not given, name is derived from the first JSON file."""
    if not input_files:
        return {"error": "No input files"}

    # Determine output filename from first JSON if not specified
    if output_path is None:
        first_file = Path(input_files[0])
        output_path = _get_ksl_dir() / (first_file.stem + ".ksl")

    combined = {"ksl_version": 1, "metadata": {}, "content": {}}
    types_found = set()
    content_count = 0

    for fpath in input_files:
        fpath = Path(fpath)
        if not fpath.exists():
            return {"error": f"File not found: {fpath}"}
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return {"error": f"Failed to read {fpath}: {e}"}

        ctype = detect_content_type(data)
        types_found.add(ctype)
        if not combined["metadata"]:
            combined["metadata"] = data.get("metadata", {})

        for key in ["notes", "quiz_topics", "quiz_metadata", "flashcards", "tutorials", "brain_qa"]:
            if key in data:
                combined["content"][key] = data[key]
                if isinstance(data[key], list):
                    content_count += len(data[key])

    final_type = content_type or (TYPE_COMBINED if len(types_found) > 1 else types_found.pop() if types_found else TYPE_NOTES)
    combined["metadata"]["content_type"] = final_type
    if title:
        combined["metadata"]["title"] = title

    json_bytes = json.dumps(combined, indent=2, ensure_ascii=False).encode("utf-8")
    header = _build_header(final_type, title or "KSLearn Package", author,
                           len(json_bytes), content_count)

    output_path = Path(output_path)
    if not output_path.suffix:
        output_path = output_path.with_suffix(".ksl")

    with open(output_path, "wb") as f:
        f.write(header)
        f.write(json_bytes)

    return {
        "output": str(output_path),
        "size": output_path.stat().st_size,
        "content_type": final_type,
        "content_count": content_count,
    }


# ═══════════════════════════════════════════════════════════════════
#  Unpack — .ksl → JSON
# ═══════════════════════════════════════════════════════════════════

def unpack_ksl(ksl_path: Path, output_dir: Path = None) -> dict:
    ksl_path = Path(ksl_path)
    if not ksl_path.exists():
        return {"error": f"File not found: {ksl_path}"}

    with open(ksl_path, "rb") as f:
        file_data = f.read()

    header_bytes = file_data[:HEADER_SIZE]
    header_info = _parse_header(header_bytes)
    if not header_info:
        return {"error": "Invalid .ksl header"}

    payload_len = header_info["payload_length"]
    json_payload = file_data[HEADER_SIZE:HEADER_SIZE + payload_len]
    data = json.loads(json_payload.decode("utf-8"))

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        ctype = header_info["type"]
        name_map = {TYPE_BRAIN: "_brain", TYPE_NOTES: "_notes", TYPE_QUIZ: "_quiz"}
        suffix = name_map.get(ctype, "")
        out_path = output_dir / (ksl_path.stem + suffix + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        header_info["extracted_file"] = str(out_path)

    header_info["data"] = data
    return header_info


# ═══════════════════════════════════════════════════════════════════
#  Info — inspect .ksl without extracting
# ═══════════════════════════════════════════════════════════════════

def info_ksl(ksl_path: Path) -> dict:
    ksl_path = Path(ksl_path)
    if not ksl_path.exists():
        return {"error": f"File not found: {ksl_path}"}
    file_size = ksl_path.stat().st_size
    with open(ksl_path, "rb") as f:
        header_bytes = f.read(HEADER_SIZE)
    info = _parse_header(header_bytes)
    if not info:
        return {"error": "Invalid .ksl file"}
    info["file"] = str(ksl_path)
    info["file_size"] = file_size
    return info


# ═══════════════════════════════════════════════════════════════════
#  Interactive Pack Mode
# ═══════════════════════════════════════════════════════════════════

def _interactive_pack():
    print("=" * 60)
    print("📦 KSLearn Package Creator (Interactive)")
    print("=" * 60)
    print()
    print("What type of .ksl package do you want to create?")
    print()
    print("  [1] 📦 Combined — Notes + Quizzes + Flashcards + Tutorials")
    print("  [2] 🧠 Brain — Knowledge Brain Q&A database (separate)")
    print()

    pkg_type = input("╰─► Choose type [1 or 2]: ").strip()
    build_type = TYPE_BRAIN if pkg_type == "2" else TYPE_COMBINED

    print()
    title = input("📝 Package name/title: ").strip()
    if not title:
        print("❌ Name cannot be empty")
        sys.exit(1)

    print()
    print("Enter paths to JSON files to include (one per line).")
    if build_type == TYPE_BRAIN:
        print("Expected: files with 'brain_qa' key (Q&A pairs).")
    else:
        print("Expected: files with 'notes', 'quiz_topics', 'flashcards', 'tutorials' keys.")
    print("Leave empty and press Enter when done.\n")

    json_files = []
    while True:
        path = input(f"  File #{len(json_files) + 1}: ").strip()
        if not path:
            break
        p = Path(path)
        if not p.exists():
            print(f"  ⚠️  File not found: {p}")
            continue
        if p.suffix != ".json":
            print(f"  ⚠️  Not a JSON file: {p}")
            continue
        json_files.append(p)
        print(f"  ✅ Added: {p.name}")

    if not json_files:
        print("❌ No JSON files added")
        sys.exit(1)

    print(f"\n📊 Analyzing {len(json_files)} file(s)...")
    all_data = {"metadata": {}, "content": {}}
    for fpath in json_files:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not all_data["metadata"]:
            all_data["metadata"] = data.get("metadata", {})
        for key in ["notes", "quiz_topics", "quiz_metadata", "flashcards", "tutorials", "brain_qa"]:
            if key in data and key not in all_data["content"]:
                all_data["content"][key] = data[key]

    data_dir = _ensure_ksl_dir()
    print(f"\n📁 Output directory: {data_dir}")
    print()

    # Use the first JSON file's name (minus extension) as the .ksl filename
    first_json = json_files[0]
    out_name = first_json.stem + ".ksl"
    out_path = data_dir / out_name

    if build_type == TYPE_BRAIN:
        _build_brain_ksl(title, all_data, json_files, out_path)
    else:
        _build_combined_ksl(title, all_data, out_path)


def _build_brain_ksl(title: str, all_data: dict, json_files: list, out_path: Path):
    brain_data = all_data["content"].get("brain_qa", [])
    if not brain_data:
        print("❌ No 'brain_qa' data found!")
        sys.exit(1)

    brain_pkg = {
        "ksl_version": 1,
        "metadata": {
            "title": f"🧠 {title}",
            "author": "kslearn",
            "created": datetime.now().isoformat(),
            "content_type": TYPE_BRAIN,
            "source_files": [str(f) for f in json_files],
        },
        "content": {"brain_qa": brain_data},
    }
    brain_json = json.dumps(brain_pkg, indent=2, ensure_ascii=False).encode("utf-8")
    header = _build_header(TYPE_BRAIN, brain_pkg["metadata"]["title"],
                           "kslearn", len(brain_json), len(brain_data))

    with open(out_path, "wb") as f:
        f.write(header)
        f.write(brain_json)

    print()
    print("=" * 60)
    print("✅ Brain KSL Package Created")
    print("=" * 60)
    print(f"\n  🧠 Knowledge Brain")
    print(f"     File:  {out_path}")
    print(f"     Size:  {out_path.stat().st_size:,} bytes")
    print(f"     Q&A:   {len(brain_data)}")
    print(f"     Source: {json_files[0].name}")


def _build_combined_ksl(title: str, all_data: dict, out_path: Path):
    combined = {
        "ksl_version": 1,
        "metadata": dict(all_data["metadata"]),
        "content": {k: v for k, v in all_data["content"].items() if k != "brain_qa"},
    }
    combined["metadata"]["content_type"] = TYPE_COMBINED
    combined["metadata"]["title"] = title

    item_count = 0
    item_count += len(combined["content"].get("notes", []))
    item_count += len(combined["content"].get("quiz_topics", []))
    item_count += len(combined["content"].get("flashcards", []))
    item_count += len(combined["content"].get("tutorials", []))

    if item_count == 0:
        print("❌ No content found! JSON must have 'notes', 'quiz_topics', 'flashcards', or 'tutorials'.")
        sys.exit(1)

    combined_json = json.dumps(combined, indent=2, ensure_ascii=False).encode("utf-8")
    header = _build_header(TYPE_COMBINED, title, "kslearn", len(combined_json), item_count)

    with open(out_path, "wb") as f:
        f.write(header)
        f.write(combined_json)

    print()
    print("=" * 60)
    print("✅ Combined KSL Package Created")
    print("=" * 60)
    print(f"\n  📦 Combined (notes+quiz+flashcards+tutorials)")
    print(f"     File:  {out_path}")
    print(f"     Size:  {out_path.stat().st_size:,} bytes")
    print(f"     Items: {item_count}")
    print(f"       📚 Notes:     {len(combined['content'].get('notes', []))}")
    print(f"       📝 Quizzes:   {len(combined['content'].get('quiz_topics', []))}")
    print(f"       🃏 Flashcards: {len(combined['content'].get('flashcards', []))}")
    print(f"       🎓 Tutorials: {len(combined['content'].get('tutorials', []))}")


# ═══════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Create and manage .ksl (KSLearn Package) files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  %(prog)s                         # Interactive\n  %(prog)s pack notes.json\n  %(prog)s pack file1.json file2.json\n  %(prog)s info content.ksl\n  %(prog)s unpack content.ksl\n",
    )
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("pack", help="Pack JSON file(s) into .ksl (name from source)")
    p.add_argument("files", nargs="+", help="JSON file(s) to pack")
    p.add_argument("-o", "--output", help="Output .ksl path (default: data/ksl/<source>.ksl)")
    p.add_argument("-t", "--title", help="Package title")

    sub.add_parser("info", help="Show .ksl file info").add_argument("file")
    sub.add_parser("unpack", help="Extract JSON from .ksl").add_argument("file")
    sub.add_parser("validate", help="Check if .ksl file is valid").add_argument("file")

    args = parser.parse_args()

    if not args.command:
        _interactive_pack()
        return

    if args.command == "pack":
        result = pack_ksl(args.files, Path(args.output) if args.output else None,
                          title=args.title)
        if "error" in result:
            print(f"❌ {result['error']}")
            sys.exit(1)
        print("=" * 60)
        print("✅ KSL Package Created")
        print("=" * 60)
        print(f"  File:  {result['output']}")
        print(f"  Size:  {result['size']:,} bytes")
        print(f"  Type:  {result['content_type']}")
        print(f"  Items: {result['content_count']}")

    elif args.command == "info":
        result = info_ksl(Path(args.file))
        if "error" in result:
            print(f"❌ {result['error']}")
            sys.exit(1)
        print("=" * 60)
        print("📋 .ksl File Info")
        print("=" * 60)
        print(f"  File:       {result['file']}")
        print(f"  Size:       {result['file_size']:,} bytes")
        print(f"  Type:       {result['type']}")
        print(f"  Title:      {result['title']}")
        print(f"  Author:     {result['author']}")
        print(f"  Created:    {result['created']}")
        print(f"  Items:      {result['content_count']}")
        print(f"  Cred:       {result['author_cred']}")
        print(f"  Version:    {result['version']}")

    elif args.command == "unpack":
        result = unpack_ksl(Path(args.file), Path("./ksl_extracted"))
        if "error" in result:
            print(f"❌ {result['error']}")
            sys.exit(1)
        print("=" * 60)
        print("📦 .ksl Package Unpacked")
        print("=" * 60)
        print(f"  Title:    {result['title']}")
        print(f"  Type:     {result['type']}")
        print(f"  Author:   {result['author']}")
        print(f"  Cred:     {result['author_cred']}")
        if result.get("extracted_file"):
            print(f"  Extracted: {result['extracted_file']}")

    elif args.command == "validate":
        ksl_path = Path(args.file)
        if not ksl_path.exists():
            print(f"❌ File not found: {ksl_path}")
            sys.exit(1)
        try:
            with open(ksl_path, "rb") as f:
                file_data = f.read()
            hdr = file_data[:HEADER_SIZE]
            h = _parse_header(hdr)
            if h is None:
                print(f"❌ {ksl_path.name}: Invalid .ksl header")
                sys.exit(1)
            payload_len = h["payload_length"]
            payload = file_data[HEADER_SIZE:HEADER_SIZE + payload_len]
            data = json.loads(payload.decode("utf-8"))
            print("=" * 60)
            print("✅ Valid .ksl File")
            print("=" * 60)
            print(f"  File:    {ksl_path}")
            print(f"  Size:    {ksl_path.stat().st_size:,} bytes")
            print(f"  Type:    {h['type']}")
            print(f"  Title:   {h['title']}")
            print(f"  Author:  {h['author']}")
            print(f"  Items:   {h['content_count']}")
            # Count content keys found
            content_keys = set()
            if isinstance(data, dict):
                for key in ["notes", "quiz_topics", "flashcards", "tutorials", "brain_qa"]:
                    if key in data:
                        content_keys.add(key)
                # Also check nested content
                content = data.get("content", {})
                for key in ["notes", "quiz_topics", "flashcards", "tutorials", "brain_qa"]:
                    if key in content:
                        content_keys.add(key)
            print(f"  Content: {', '.join(sorted(content_keys)) if content_keys else 'none found'}")
        except json.JSONDecodeError as e:
            print(f"❌ {ksl_path.name}: Invalid file format — bad JSON: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ {ksl_path.name}: Invalid file format — {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
