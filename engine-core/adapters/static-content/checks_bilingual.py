#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""双语对照适配器（迁移自主站 tests/check-bilingual.py）。

同 checks_structure.py：**委托执行 + 解析结论**，不重写。
理由相同（不重写已验证的资产），代价也相同（接进报告层，尚未接进规则层）。

这个脚本检查两类东西（原脚本文件头列得很清楚）：
  A. 逐行对照：段数是否相等、有无单侧语言、公式两侧是否逐字一致、
     数字/节号是否对应、中英行的 lang 属性
  B. 视频入口：每个小节是否有顶部与底部入口、两处是否指向同一组 URL、
     外链是否带 target="_blank" + rel="noopener noreferrer"

它的输出有三档，含义不同，解析时要分开：
  ① 硬性问题（issues）—— 影响退出码
  ② 「行内符号出现次数不同」—— 行文差异，**供人工确认，不阻断**
  ③ 「数字/节号两侧不完全对应」—— **供人工确认，不阻断**

把 ②③ 也算成失败会让校验长期红灯（原脚本刻意不计入退出码），
所以本适配器沿用同一口径：只有 ① 影响 pass。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

LEGACY_REL = os.path.join('tests', 'check-bilingual.py')


def _triple(pass_, reason='', certificate=None):
    return {'pass': bool(pass_), 'reason': reason, 'certificate': certificate}


#: 硬性通过的那句（原脚本成功路径的固定措辞）
HARD_OK_RE = re.compile(r'✓\s*硬性检查通过（([^）]*)）')
HARD_OK_ALL_RE = re.compile(r'✓\s*双语对照与视频入口检查全部通过')
#: 供人工确认的两档
DETAIL_RE = re.compile(r'行内符号出现次数不同\s*(\d+)\s*处')
NUM_RE = re.compile(r'数字/节号两侧不完全对应\s*(\d+)\s*处')
#: 硬性问题与「供人工确认」的条目**都用 · 开头**，所以不能见到 · 就当问题。
#: 只有出现在「发现 N 个问题」这行之后（且直到下一个空行之前）的才算硬性问题。
#: （第一版没做这个区分，把 121 条行文差异 + 10 条节号差异全当成了硬性问题，
#:   于是 pass 被判成 False —— 而原脚本退出码是 0。又是「范围没划对」。）
ISSUE_HEADER_RE = re.compile(r'发现\s*(\d+)\s*个问题[^\n]*\n')
BULLET_RE = re.compile(r'^\s*[•·]\s*(.+)$')
ANY_BULLET_RE = re.compile(r'^\s*[•·]\s*(.+)$', re.M)


def _bullets_after(text, start):
    """取 start 之后、直到遇到非 · 开头的非空行之前的所有条目。"""
    items = []
    for line in text[start:].split('\n'):
        s = line.strip()
        if not s:
            if items:
                break
            continue
        m = BULLET_RE.match(line)
        if m:
            items.append(m.group(1).strip())
        elif items:
            break
    return items


def _issues_after_header(out):
    """硬性问题：只收「发现 N 个问题」之后的条目。"""
    m = ISSUE_HEADER_RE.search(out)
    if not m:
        return []
    return _bullets_after(out, m.end())


def _samples_after(out, header_re):
    """某一档「供人工确认」的条目前几条。"""
    m = header_re.search(out)
    if not m:
        return []
    return _bullets_after(out, m.end())[:6]


def parse(root):
    legacy = os.path.join(root, LEGACY_REL)
    if not os.path.isfile(legacy):
        # 宿主站点没有带这个脚本 —— 这是**正常情形**，不是失败。
        # 本适配器是「委托执行」式的：宿主脚本不在，这一项就没得可查。
        # 报成失败会误导使用者（把「没装那个脚本」看成「内容有问题」）。
        # （交付给第三方开发者的包里就没有这两个脚本，本项目实测到过。）
        return _triple(True, '', {'skipped': True, 'legacy': LEGACY_REL,
                                  'why': '宿主站点未提供 %s，本项跳过' % LEGACY_REL})

    r = subprocess.run([sys.executable, legacy], capture_output=True, text=True, cwd=root)
    out = (r.stdout or '') + (r.stderr or '')

    cert = {'exitCode': r.returncode, 'legacy': LEGACY_REL}

    m = DETAIL_RE.search(out)
    cert['inlineSymbolDiff'] = int(m.group(1)) if m else 0
    m = NUM_RE.search(out)
    cert['numberMismatch'] = int(m.group(1)) if m else 0

    hard = HARD_OK_RE.search(out) or HARD_OK_ALL_RE.search(out)
    if hard:
        cert['hardChecks'] = hard.group(1) if hard.groups() else '全部通过'
        cert['allClean'] = bool(HARD_OK_ALL_RE.search(out))

    issues = _issues_after_header(out)
    cert['issues'] = issues
    cert['issueSamples'] = issues[:8]
    # 另外两档也留一份（供人工确认，不影响 pass）
    cert['inlineSamples'] = _samples_after(out, DETAIL_RE)
    cert['numberSamples'] = _samples_after(out, NUM_RE)

    if issues:
        return _triple(False, '硬性检查未通过：%s' % '；'.join(issues[:3]), cert)
    if r.returncode != 0:
        return _triple(False, '原脚本退出码 %d，但未解析到问题条目（输出格式可能已变）'
                       % r.returncode, cert)
    if not hard:
        # 退出码为 0 却找不到成功措辞：说明输出格式变了，必须报出来
        return _triple(False, '原脚本退出码 0，但未解析到硬性检查的结论行（输出格式可能已变）',
                       cert)
    return _triple(True, '', cert)


CHECKS = [
    ('bilingual', '双语对照 / 视频入口', parse),
]
