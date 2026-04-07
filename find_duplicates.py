#!/usr/bin/env python3
"""
File Duplication Finder
=======================
Scans a directory for files with identical content.
For standard files, it uses SHA-256 binary hashing.
For PDF files, it extracts the internal text and hashes the text content,
allowing it to group PDFs that look the same but have different metadata.

Usage:
    python find_duplicates.py <folder_path> [--extensions .txt .pdf ...]
    python find_duplicates.py <folder_path> --all-files
    python find_duplicates.py <folder_path> --report report.json
"""

import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Try to import PyPDF2 for PDF text extraction support
try:
    import PyPDF2
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False


# ──────────────────────────────────────────────────────
#  Default extensions to scan
# ──────────────────────────────────────────────────────
DEFAULT_EXTENSIONS = [
    ".pdf", ".txt", ".md", ".csv", ".log", ".json", ".xml",
    ".yaml", ".yml", ".ini", ".cfg", ".conf",
    ".py", ".js", ".ts", ".html", ".css", ".scss",
    ".java", ".c", ".cpp", ".h", ".hpp",
    ".sh", ".bash", ".zsh", ".bat", ".ps1",
    ".rst", ".tex", ".toml", ".env",
]


def hash_binary_file(filepath: str) -> str:
    """Calculate SHA-256 hash of a file's binary content."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return "BIN_" + sha256.hexdigest()


def hash_pdf_text(filepath: str) -> str:
    """
    Attempt to extract text from a PDF and hash it.
    Falls back to binary hashing if extraction fails or yields no text.
    """
    if not HAS_PYPDF:
        return hash_binary_file(filepath)

    text_content = []
    try:
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text_content.append(extracted)
        
        full_text = "".join(text_content).strip()
        
        # If the PDF is completely image-based (no selectable text), fallback to binary
        if not full_text:
            return hash_binary_file(filepath)
            
        sha256 = hashlib.sha256()
        sha256.update(full_text.encode("utf-8"))
        return "TXT_" + sha256.hexdigest()
        
    except Exception as e:
        # If the PDF is encrypted, corrupted, or unsupported, fallback to binary
        return hash_binary_file(filepath)


def should_include(filepath: str, extensions: list[str] | None, all_files: bool) -> bool:
    """Determine if a file should be included in the scan."""
    if all_files:
        return True
    ext = Path(filepath).suffix.lower()
    target_exts = extensions if extensions else DEFAULT_EXTENSIONS
    return ext in target_exts


def find_duplicates(
    folder: str,
    extensions: list[str] | None = None,
    all_files: bool = False,
    recursive: bool = True,
) -> tuple[dict[str, list[str]], int]:
    """
    Find duplicate files in a folder.
    Returns: (duplicates_dict, total_files_scanned)
    """
    hash_map: dict[str, list[str]] = defaultdict(list)
    total_files = 0

    if recursive:
        walker = os.walk(folder)
    else:
        try:
            entries = os.listdir(folder)
        except PermissionError as e:
            print(f"  ⚠ Cannot access: {folder} ({e})", file=sys.stderr)
            return {}, 0
        walker = [(folder, [], [f for f in entries if os.path.isfile(os.path.join(folder, f))])]

    for root, _, files in walker:
        for filename in files:
            filepath = os.path.join(root, filename)

            if not should_include(filepath, extensions, all_files):
                continue

            total_files += 1
            try:
                # Use text hashing for PDFs, binary hashing for everything else
                if filepath.lower().endswith(".pdf"):
                    file_hash = hash_pdf_text(filepath)
                else:
                    file_hash = hash_binary_file(filepath)
                    
                hash_map[file_hash].append(filepath)
            except (PermissionError, OSError) as e:
                print(f"  ⚠ Could not read: {filepath} ({e})", file=sys.stderr)

    # Keep only groups with duplicates (2+ files with same hash)
    duplicates = {h: paths for h, paths in hash_map.items() if len(paths) > 1}
    return duplicates, total_files


def format_size(size_bytes: int | float) -> str:
    """Format file size in human-readable form."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def print_results(duplicates: dict[str, list[str]], total_files: int) -> None:
    """Print duplicate file groups in a readable format."""
    if not duplicates:
        print(f"\n✅ No duplicate files found among {total_files} files scanned.")
        return

    total_groups = len(duplicates)
    total_dupes = sum(len(paths) for paths in duplicates.values())
    wasted_space = 0

    print(f"\n{'='*60}")
    print(f"  DUPLICATE FILES REPORT")
    print(f"{'='*60}")
    print(f"  Files scanned : {total_files}")
    print(f"  Duplicate groups : {total_groups}")
    print(f"  Total duplicate files : {total_dupes}")
    print(f"{'='*60}\n")

    for i, (file_hash, paths) in enumerate(duplicates.items(), 1):
        try:
            file_size = os.path.getsize(paths[0])
        except OSError:
            file_size = 0
            
        # For text-based PDF matches, sizes might differ. Calculate actual waste.
        sizes = [os.path.getsize(p) for p in paths]
        group_waste = sum(sizes) - min(sizes) # Keeping the smallest file saves the rest
        wasted_space += group_waste

        match_type = "Text Content" if selected_hash_is_txt(file_hash) else "Binary Content"

        print(f"  📁 Group {i} — {len(paths)} identical files (Match: {match_type})")
        print(f"  {'─'*50}")
        for path in sorted(paths):
            sz = os.path.getsize(path)
            print(f"    • {path} ({format_size(sz)})")
        print()

    print(f"{'='*60}")
    print(f"  💾 Potential space savings by deleting duplicates: {format_size(wasted_space)}")
    print(f"{'='*60}\n")


def selected_hash_is_txt(file_hash: str) -> bool:
    return file_hash.startswith("TXT_")


def export_report(
    duplicates: dict[str, list[str]],
    total_files: int,
    folder: str,
    output_path: str,
) -> None:
    """Export results to a JSON report file."""
    report = {
        "scan_info": {
            "scanned_folder": os.path.abspath(folder),
            "timestamp": datetime.now().isoformat(),
            "total_files_scanned": total_files,
            "duplicate_groups": len(duplicates),
            "total_duplicate_files": sum(len(p) for p in duplicates.values()),
        },
        "duplicate_groups": [],
    }

    for file_hash, paths in duplicates.items():
        files_info = []
        for p in paths:
            sz = os.path.getsize(p)
            files_info.append({
                "path": p,
                "size_bytes": sz,
                "size_human": format_size(sz)
            })
            
        match_type = "Text Content" if selected_hash_is_txt(file_hash) else "Binary Content"

        report["duplicate_groups"].append({
            "hash": file_hash,
            "match_type": match_type,
            "count": len(paths),
            "files": files_info,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"  📄 Report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Find duplicate text and PDF files in a directory.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("folder", help="Path to the folder to scan")
    parser.add_argument("--extensions", nargs="+", default=None,
                        help="File extensions to check (e.g., .pdf .txt .md)")
    parser.add_argument("--all-files", action="store_true",
                        help="Check ALL files, not just text/PDF files")
    parser.add_argument("--no-recursive", action="store_true",
                        help="Do NOT scan subdirectories (only top-level)")
    parser.add_argument("--report", default=None, metavar="FILE",
                        help="Export results to a JSON report file")

    args = parser.parse_args()

    folder = os.path.abspath(args.folder)
    if not os.path.isdir(folder):
        print(f"❌ Error: '{folder}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)
        
    if not HAS_PYPDF:
        print("  ⚠ PyPDF2 is not installed! PDF text comparison will fall back to binary comparison.", file=sys.stderr)
        print("    To fix: pip install PyPDF2", file=sys.stderr)

    # Display scan configuration
    print(f"\n🔍 Scanning: {folder}")
    if args.all_files:
        print(f"   Mode       : All files")
    elif args.extensions:
        print(f"   Extensions : {', '.join(args.extensions)}")
    else:
        print(f"   Mode       : Default documents and text file extensions (including .pdf)")
    print(f"   Recursive  : {'No' if args.no_recursive else 'Yes'}")

    duplicates, total_files = find_duplicates(
        folder,
        extensions=args.extensions,
        all_files=args.all_files,
        recursive=not args.no_recursive,
    )

    print_results(duplicates, total_files)

    if args.report:
        export_report(duplicates, total_files, folder, args.report)


if __name__ == "__main__":
    main()
