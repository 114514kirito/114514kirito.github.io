#!/usr/bin/env python3
"""
Extract bilingual xv6 book content from Immersive Translate HTML
and generate markdown files for each chapter.
"""

import re
import os
import sys
from bs4 import BeautifulSoup, NavigableString, Tag, Comment


def extract_bilingual(element):
    """Extract English and Chinese text from a bilingual HTML element."""
    english_parts = []
    chinese_parts = []

    def is_translation_wrapper(node):
        if not isinstance(node, Tag) or node.name != 'font':
            return False
        return 'immersive-translate-target-wrapper' in node.get('class', [])

    def is_math_el(node):
        if not isinstance(node, Tag):
            return False
        return node.name in ('svg', 'mjx-container', 'math', 'mathml',
                             'mathmlword', 'asciimath', 'latex', 'clipboard-copy')

    def walk(node, in_trans=False):
        if isinstance(node, NavigableString):
            text = str(node)
            (chinese_parts if in_trans else english_parts).append(text)
            return
        if not isinstance(node, Tag):
            return
        if is_math_el(node):
            return
        if node.name == 'span' and 'math-inline' in node.get('class', []):
            return
        if is_translation_wrapper(node):
            for child in node.children:
                walk(child, in_trans=True)
            return
        for child in node.children:
            walk(child, in_trans)

    walk(element)

    def clean(s):
        return re.sub(r'\s+', ' ', s).strip()

    return clean(''.join(english_parts)), clean(''.join(chinese_parts))


def extract_code(pre_el):
    """Extract code text from a <pre> element, excluding clipboard-copy artifacts."""
    parts = []
    for child in pre_el.descendants:
        if isinstance(child, NavigableString):
            parts.append(str(child))
    code = ''.join(parts).strip()
    # Unescape HTML entities
    code = code.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')
    return code


def is_code_wrapper(el):
    """Check if a div is a code block wrapper."""
    if not isinstance(el, Tag) or el.name != 'div':
        return False
    style = el.get('style', '')
    return 'overflow: auto' in style and el.find('pre') is not None


def get_cleaned_text(element):
    """Get just the visible text from an element, stripping translation markup."""
    text = []
    for child in element.descendants:
        if isinstance(child, NavigableString):
            t = str(child).strip()
            if t:
                text.append(t)
    return ' '.join(text).strip()


def main():
    html_path = "/home/kirito/blog/YukinoBlog/book-riscv-rev5-zh-CN-dual.html"
    output_dir = "/home/kirito/blog/YukinoBlog/src/xv6-riscv-book"

    print("Loading HTML...")
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    preview = soup.find('div', id='preview-content')
    if not preview:
        print("ERROR: Cannot find #preview-content")
        return 1

    print("Parsing content...")

    # Get all direct children of preview-content
    elements = [el for el in preview.children if isinstance(el, Tag)]

    # Parse into chapters
    current_chapter = None
    chapters = {}  # chapter_num -> list of (type, data...) tuples

    # Track code blocks that should be merged
    pending_code = None

    def flush_code():
        nonlocal pending_code
        if pending_code is not None and current_chapter:
            chapters[current_chapter].append(('code', pending_code))
            pending_code = None

    for el in elements:
        tag = el.name

        # ---- Chapter headers (h2) ----
        if tag == 'h2':
            flush_code()

            # Skip initial h1 (main title) - it's the book title
            if el.get('type') == 'title':
                continue

            el_id = el.get('id', '')

            if el_id.startswith('chapter-'):
                try:
                    current_chapter = int(el_id.split('-')[1])
                except ValueError:
                    continue
                if current_chapter not in chapters:
                    chapters[current_chapter] = []
                continue

            # Check if this is a TOC heading or foreword - skip
            if el_id in ('contents', 'foreword-and-acknowledgments'):
                continue

            # This is a chapter title h2
            eng, chn = extract_bilingual(el)
            if current_chapter and eng:
                chapters[current_chapter].append(('chapter_title', eng, chn))

        # ---- Section headers (h3) ----
        elif tag == 'h3' and current_chapter:
            flush_code()
            el_id = el.get('id', '')
            eng, chn = extract_bilingual(el)
            if eng:
                chapters[current_chapter].append(('section', el_id, eng, chn))

        # ---- DIV elements ----
        elif tag == 'div' and current_chapter:
            # Code wrapper
            if is_code_wrapper(el):
                code = extract_code(el.find('pre'))
                if code:
                    if pending_code is not None:
                        # Merge with previous code block
                        pending_code += '\n' + code
                    else:
                        pending_code = code
                continue

            # Paragraph with translation
            if el.get('data-imt-p') == '1':
                flush_code()
                eng, chn = extract_bilingual(el)
                if eng or chn:
                    chapters[current_chapter].append(('p', eng, chn))
                continue

            # Check class
            classes = el.get('class', [])

            # Figure caption
            if 'caption_figure' in classes:
                flush_code()
                eng, chn = extract_bilingual(el)
                chapters[current_chapter].append(('caption', eng, chn))
                continue

            # Figure image
            if 'figure_img' in classes:
                flush_code()
                img = el.find('img')
                src = img.get('src', '') if img else ''
                chapters[current_chapter].append(('figure', src))
                continue

            # Table
            if 'table' in classes:
                flush_code()
                headers = []
                rows = []

                thead = el.find('thead')
                if thead:
                    for th in thead.find_all('th'):
                        he, hc = extract_bilingual(th)
                        headers.append((he, hc))

                tbody = el.find('tbody')
                if tbody:
                    for tr in tbody.find_all('tr'):
                        row = []
                        for td in tr.find_all('td'):
                            code_el = td.find('code')
                            if code_el:
                                row.append(('`' + code_el.get_text().strip() + '`', ''))
                            else:
                                te, tc = extract_bilingual(td)
                                row.append((te, tc))
                        rows.append(row)

                chapters[current_chapter].append(('table', headers, rows))
                continue

        # ---- Code blocks (direct pre, unwrapped) ----
        elif tag == 'pre' and current_chapter:
            code = extract_code(el)
            if code:
                if pending_code is not None:
                    pending_code += '\n' + code
                else:
                    pending_code = code
            continue

        # ---- Lists (ul) ----
        elif tag == 'ul' and current_chapter:
            flush_code()
            items = []
            for li in el.find_all('li', recursive=False):
                ie, ic = extract_bilingual(li)
                if ie or ic:
                    items.append((ie, ic))
            if items:
                chapters[current_chapter].append(('list', items))
            continue

        # ---- Paragraph ----
        elif tag == 'p' and current_chapter:
            flush_code()
            eng, chn = extract_bilingual(el)
            if eng or chn:
                chapters[current_chapter].append(('p', eng, chn))
            continue

        # ---- Ordered lists ----
        elif tag == 'ol' and current_chapter:
            flush_code()
            items = []
            for li in el.find_all('li', recursive=False):
                ie, ic = extract_bilingual(li)
                if ie or ic:
                    items.append((ie, ic))
            if items:
                chapters[current_chapter].append(('olist', items))
            continue

    # Flush any remaining code
    flush_code()

    print(f"Extracted {len(chapters)} chapters: {sorted(chapters.keys())}")
    for cn, items in sorted(chapters.items()):
        types = {}
        for t, *_ in items:
            types[t] = types.get(t, 0) + 1
        print(f"  Chapter {cn}: {len(items)} elements - {types}")

    # ---- Chapter metadata ----
    # HTML chapter numbering (rev5): 1-8 match, 9=Sleep/Wakeup, 10=File system, 11-12=appendices
    # Repo directories: chapter1-chapter9
    # Mapping: HTML 1-8 → repo 1-8, HTML 10 → repo 9, skip HTML 9,11,12
    chapter_meta = {
        1:  {"en": "Operating system interfaces", "cn": "操作系统接口", "dir": "chapter1"},
        2:  {"en": "Operating system organization", "cn": "操作系统组织结构", "dir": "chapter2"},
        3:  {"en": "Page tables", "cn": "页表", "dir": "chapter3"},
        4:  {"en": "Traps and system calls", "cn": "Trap 与系统调用", "dir": "chapter4"},
        5:  {"en": "Page faults", "cn": "缺页异常", "dir": "chapter5"},
        6:  {"en": "Interrupts and device drivers", "cn": "中断与设备驱动程序", "dir": "chapter6"},
        7:  {"en": "Locking", "cn": "锁机制", "dir": "chapter7"},
        8:  {"en": "Scheduling", "cn": "调度", "dir": "chapter8"},
        # HTML chapter 9 = "Sleep and Wakeup" - new in rev5, no repo dir yet
        9:  {"en": "Sleep and Wakeup", "cn": "休眠与唤醒", "dir": None},  # skip - no dir
        10: {"en": "File system", "cn": "文件系统", "dir": "chapter9"},
        11: {"en": "Summary", "cn": "总结", "dir": None},  # appendix - skip
        12: {"en": "Index", "cn": "索引", "dir": None},    # appendix - skip
    }

    # Generate markdown
    print("\nGenerating markdown files...")

    for cn in sorted(chapters.keys()):
        meta = chapter_meta.get(cn, {"en": f"Chapter {cn}", "cn": f"第{cn}章", "dir": None})
        dir_name = meta["dir"]

        # Skip chapters that don't map to a directory
        if dir_name is None:
            print(f"  Skipping HTML chapter {cn} ({meta['en']}) - no repo directory")
            continue

        items = chapters[cn]

        lines = []
        # Frontmatter - use repo chapter number
        repo_cn = int(dir_name.replace('chapter', ''))
        lines.append("---")
        lines.append(f"title: xv6 riscv book chapter {repo_cn}：{meta['en']}")
        lines.append("date: 2025-07-27")
        lines.append("tag: ")
        lines.append("- OS")
        lines.append("- risc-v")
        lines.append("category: ")
        lines.append("- OS")
        lines.append("- risc-v")
        lines.append("---")
        lines.append("")
        lines.append(f"# xv6 riscv book chapter {repo_cn}：{meta['en']}")
        lines.append("")

        for item in items:
            typ = item[0]

            if typ == 'chapter_title':
                continue  # skip, already in h1

            elif typ == 'section':
                _, sec_id, eng, chn = item
                # Extract just the section number from the ID
                sec_num = ''
                m = re.match(r'(\d+\.\d+)', sec_id)
                if m:
                    sec_num = m.group(1)
                else:
                    sec_num = sec_id.split('-')[0]

                # Remove leading section number from English title if it duplicates
                eng_title = eng
                if sec_num and eng.startswith(sec_num):
                    eng_title = eng[len(sec_num):].lstrip()

                lines.append(f"## {sec_num} {eng_title}")
                lines.append("")

            elif typ == 'p':
                eng, chn = item[1], item[2]
                if eng and chn:
                    lines.append(eng)
                    lines.append("")
                    lines.append(chn)
                elif eng:
                    lines.append(eng)
                elif chn:
                    lines.append(chn)
                lines.append("")

            elif typ == 'code':
                code = item[1]
                # Detect language
                if code.startswith('#') or 'objdump' in code:
                    lang = 'bash'
                elif re.match(r'^echo\s|^\$|^cat\s|^grep\s', code):
                    lang = 'sh'
                else:
                    lang = 'c'
                lines.append(f"```{lang}")
                # Unescape HTML entities in code
                lines.append(code)
                lines.append("```")
                lines.append("")

            elif typ == 'figure':
                # Just note the figure
                lines.append(f"![Figure](image/placeholder.png)")
                lines.append("")

            elif typ == 'caption':
                eng, chn = item[1], item[2]
                if eng:
                    lines.append(f"*{eng}*")
                lines.append("")

            elif typ == 'table':
                headers, rows = item[1], item[2]
                is_syscall = any('System call' in str(h[0]) for h in headers)
                if is_syscall:
                    lines.append('<center-panel natural title="（Figure 1.2: xv6 system calls. If not otherwise stated, these calls return 0 for no error, and -1 if there\'s an error）">')
                    lines.append("")
                    lines.append("| **System call**                               | **Description**                                                                 |")
                    lines.append("|----------------------------------------------|---------------------------------------------------------------------------------|")
                    for row in rows:
                        call = row[0][0] if row else ""
                        desc = row[1][0] if len(row) > 1 else ""
                        lines.append(f"| {call} | {desc} |")
                    lines.append("")
                    lines.append("</center-panel>")
                    lines.append("")
                else:
                    if headers:
                        hdr = " | ".join(h[0] for h in headers)
                        lines.append(f"| {hdr} |")
                        lines.append("|" + "|".join("---" for _ in headers) + "|")
                    for row in rows:
                        cells = " | ".join(c[0] for c in row)
                        lines.append(f"| {cells} |")
                    lines.append("")

            elif typ == 'list':
                for eng, chn in item[1]:
                    if eng and chn:
                        lines.append(f"- {eng}")
                        lines.append(f"  {chn}")
                    elif eng:
                        lines.append(f"- {eng}")
                lines.append("")

            elif typ == 'olist':
                for i, (eng, chn) in enumerate(item[1], 1):
                    if eng and chn:
                        lines.append(f"{i}. {eng}")
                        lines.append(f"   {chn}")
                    elif eng:
                        lines.append(f"{i}. {eng}")
                lines.append("")

        # Write file
        md_path = os.path.join(output_dir, dir_name, "README.md")
        os.makedirs(os.path.dirname(md_path), exist_ok=True)

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')

        content_lines = sum(1 for l in lines if l.strip())
        print(f"  {dir_name}/README.md: {content_lines} content lines, {len(items)} elements")

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
