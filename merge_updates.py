#!/usr/bin/env python3
"""Merge update .txt files into original directory.

Usage: python merge_updates.py <original_dir> <update_dir>

For each .txt file in update_dir (recursively), merge it into the corresponding
location in original_dir according to the following rules:

- New files (not in original) are copied directly.
- New entry numbers are added to the original file, sorted by number.
- For duplicate entry numbers:
  - '<' lines: keep original if exists, otherwise use update
- '>' lines: original's '>' becomes 'O', placed below '<'; update's '>' kept as '>'
- '-' lines: original's '-' becomes 'C', placed below '>'; update's '-' kept as '-'
  - '=' lines: use update's '=' directly
"""

import sys
import os
import re
from pathlib import Path
from collections import OrderedDict


def parse_file(filepath):
    """Parse a .txt file into an OrderedDict of entry_number -> list of (prefix, line)."""
    entries = OrderedDict()
    if not os.path.exists(filepath):
        return entries

    with open(filepath, 'r', encoding='utf-8') as f:
        current_num = None
        for line in f:
            line = line.rstrip('\n\r')
            if not line:
                continue
            m = re.match(r'^([<>=OC])\s+(\d+):', line)
            if m:
                prefix = m.group(1)
                num = int(m.group(2))
                current_num = num
                if num not in entries:
                    entries[num] = []
                entries[num].append((prefix, line))
            elif current_num is not None and current_num in entries:
                entries[current_num].append(('', line))
    return entries


def merge_entries(orig_entries, update_entries):
    """Merge update entries into original entries. Returns merged OrderedDict."""
    merged = OrderedDict()
    all_nums = sorted(set(list(orig_entries.keys()) + list(update_entries.keys())))

    for num in all_nums:
        orig_lines = orig_entries.get(num, [])
        update_lines = update_entries.get(num, [])

        if not update_lines:
            merged[num] = orig_lines
        elif not orig_lines:
            merged[num] = update_lines
        else:
            result = []

            orig_map = {}
            for prefix, line in orig_lines:
                if prefix in ('<', '>', '-', '='):
                    orig_map[prefix] = line

            update_map = {}
            for prefix, line in update_lines:
                if prefix in ('<', '>', '-', '='):
                    update_map[prefix] = line

            # '<' - keep original if exists, otherwise use update
            if '<' in orig_map:
                result.append(('<', orig_map['<']))
            elif '<' in update_map:
                result.append(('<', update_map['<']))

            # 'O' - original's '>' renamed
            if '>' in orig_map:
                o_line = 'O' + orig_map['>'][1:]
                result.append(('O', o_line))

            # '>' - use update's '>'
            if '>' in update_map:
                result.append(('>', update_map['>']))

            # '-' - use update's '-'
            if '-' in update_map:
                result.append(('-', update_map['-']))

            # 'C' - original's '=' renamed (old MOD Chinese translation)
            if '=' in orig_map:
                c_line = 'C' + orig_map['='][1:]
                result.append(('C', c_line))

            # '=' - use update's '='
            if '=' in update_map:
                result.append(('=', update_map['=']))
            elif '=' in orig_map:
                result.append(('=', orig_map['=']))

            merged[num] = result

    return merged


def write_file(filepath, entries):
    """Write merged entries back to file with LF line endings."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        for num, lines in entries.items():
            for prefix, line in lines:
                f.write(line + '\n')


def merge_directories(orig_dir, update_dir):
    """Merge all .txt files from update_dir into orig_dir."""
    orig_path = Path(orig_dir)
    update_path = Path(update_dir)

    update_files = sorted(update_path.rglob('*.txt'))

    stats = {'new_files': 0, 'merged_files': 0, 'new_entries': 0, 'merged_entries': 0}

    for update_file in update_files:
        rel_path = update_file.relative_to(update_path)
        orig_file = orig_path / rel_path

        update_entries = parse_file(str(update_file))

        if not orig_file.exists():
            write_file(str(orig_file), update_entries)
            stats['new_files'] += 1
            print(f"  [NEW]   {rel_path}")
        else:
            orig_entries = parse_file(str(orig_file))

            new_count = sum(1 for n in update_entries if n not in orig_entries)
            dup_count = sum(1 for n in update_entries if n in orig_entries)

            merged = merge_entries(orig_entries, update_entries)
            write_file(str(orig_file), merged)

            stats['merged_files'] += 1
            stats['new_entries'] += new_count
            stats['merged_entries'] += dup_count
            print(f"  [MERGE] {rel_path} (+{new_count} new, ~{dup_count} merged)")

    return stats


def main():
    if len(sys.argv) != 3:
        print("Usage: python merge_updates.py <original_dir> <update_dir>")
        print()
        print("Example:")
        print("  python merge_updates.py . update")
        sys.exit(1)

    orig_dir = sys.argv[1]
    update_dir = sys.argv[2]

    if not os.path.isdir(orig_dir):
        print(f"Error: original directory not found: {orig_dir}")
        sys.exit(1)
    if not os.path.isdir(update_dir):
        print(f"Error: update directory not found: {update_dir}")
        sys.exit(1)

    print(f"Original: {orig_dir}")
    print(f"Update:   {update_dir}")
    print()

    stats = merge_directories(orig_dir, update_dir)

    print()
    print(f"Done: {stats['new_files']} new files, {stats['merged_files']} merged files")
    print(f"      {stats['new_entries']} new entries, {stats['merged_entries']} merged entries")


if __name__ == '__main__':
    main()
