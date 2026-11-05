#!/usr/bin/env python3
"""補充されたTipsファイルを正規化

claudeが出力にコードブロック(```)や前置き文を混ぜることがあるため、
- 先頭の余計な部分を除去（最初の '---\\nid:' から始まるように）
- frontmatterのYAMLパース検証
- 不正ファイルは削除

Usage: normalize-tips.py FILE [FILE...]
"""
import re
import sys
from pathlib import Path

import yaml


def normalize(file_path: str) -> tuple[bool, str]:
    p = Path(file_path)
    if not p.exists():
        return False, "not exists"

    content = p.read_text(encoding="utf-8")

    # 先頭から '---\nid:' を探し、それより前を削除
    m = re.search(r"^---\s*\nid:", content, re.MULTILINE)
    if not m:
        return False, "no '---\\nid:' marker found"
    if m.start() > 0:
        content = content[m.start():]
        p.write_text(content, encoding="utf-8")

    # frontmatter検証
    fm = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if not fm:
        return False, "frontmatter not closed"
    try:
        md = yaml.safe_load(fm.group(1))
    except yaml.YAMLError as e:
        return False, f"YAML error: {e}"
    if not isinstance(md, dict):
        return False, f"frontmatter is {type(md).__name__}"
    if not md.get("id"):
        return False, "no id field"

    # IDはファイル名に揃える（生成AIが番号をずらして書くとIDが重複し、同じTipsが配信され続けるため）
    if str(md["id"]) != p.stem:
        content = re.sub(r'^id:.*$', f'id: "{p.stem}"', content, count=1, flags=re.MULTILINE)
        p.write_text(content, encoding="utf-8")
        print(f"[FIXED] {p.name}: id {md['id']} -> {p.stem}", file=sys.stderr)

    return True, "ok"


def main():
    valid = 0
    invalid = 0
    for f in sys.argv[1:]:
        ok, msg = normalize(f)
        if ok:
            valid += 1
        else:
            invalid += 1
            print(f"[INVALID] {f}: {msg}", file=sys.stderr)
            Path(f).unlink(missing_ok=True)
    print(f"normalized: valid={valid} invalid={invalid}")
    sys.exit(0 if invalid == 0 else 1)


if __name__ == "__main__":
    main()
