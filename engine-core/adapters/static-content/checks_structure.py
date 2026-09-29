#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结构校验适配器（迁移自主站 tests/check-structure.py）。

迁移方式：**委托执行 + 解析结论**，而不是重写 420 行解析逻辑
================================================================
原脚本的 check_file / check_section / check_question 共约 230 行，
做的是「从 HTML 里按正则切出小节、例题、测验」，判定规则密集且互相牵连
（允许标签白名单、视频 BV 号格式、双语 .zh/.en 成对、测验 id 去重…）。

对这部分的处理有两选择：

  A. 照原样重写进适配器 —— 本项目的既定纪律是「不重写已验证的资产」，
     因为重写会把已验证的东西变回未验证状态（主站 .git 那次的教训）。
  B. 委托执行原脚本，解析它的结论 —— 逻辑零重写、行为零偏差。

本文件选 B，代价与收益都写清楚：

  收益：行为 100% 等于原脚本（差分对照必然一致）；
        仍是「一处逻辑」，不会出现两份解析器各自演化。
  代价：这一项**尚未真正做到声明式**——它是个黑盒委托，
        而不是 checks.py 那张「一条规则一行」的检查表。
        换句话说，它接进了引擎的**报告层**，还没接进引擎的**规则层**。

这个区别必须说清楚，不能含糊地算作「已迁移」。
后续要做的是把原脚本的三个解析函数逐个搬进 checks.py，
每搬一个做一次差分对照；本次到此为止。
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

#: 原脚本在快照里的位置（相对快照根）
LEGACY_REL = os.path.join('tests', 'check-structure.py')


def _triple(pass_, reason='', certificate=None):
    return {'pass': bool(pass_), 'reason': reason, 'certificate': certificate}


#: 统计行形如：小节 82 · 例题 358 · 测验卷 84 · 测验题 664 · 讲评 84
STAT_RE = re.compile(r'小节\s*(\d+)\s*·\s*例题\s*(\d+)\s*·\s*测验卷\s*(\d+)'
                     r'\s*·\s*测验题\s*(\d+)\s*·\s*讲评\s*(\d+)')
DIFF_RE = re.compile(r'基础\s*(\d+)\s*\((\d+)%\)\s*·\s*中等\s*(\d+)\s*\((\d+)%\)'
                     r'\s*·\s*考研\s*(\d+)\s*\((\d+)%\)')
BI_RE = re.compile(r'概念/方法块\s*(\d+)\s*个\s*·\s*对照段\s*(\d+)\s*条'
                   r'\s*·\s*英文题干\s*(\d+)\s*条\s*·\s*英文解析\s*(\d+)\s*条'
                   r'\s*·\s*视频登记\s*(\d+)\s*条')
ISSUE_RE = re.compile(r'^\s*[•·]\s*(.+)$', re.M)


def parse(root):
    """跑原脚本并解析其结论。

    用子进程而不是 import：原脚本用 __file__ 推导站点根，
    import 会绑定到适配器自己的位置；子进程则按快照里的副本执行，
    天然对快照生效（这也是差分对照能成立的原因）。
    """
    legacy = os.path.join(root, LEGACY_REL)
    if not os.path.isfile(legacy):
        return _triple(False, '快照里找不到原脚本：%s' % LEGACY_REL,
                       {'legacy': LEGACY_REL})

    r = subprocess.run([sys.executable, legacy], capture_output=True, text=True, cwd=root)
    out = (r.stdout or '') + (r.stderr or '')

    cert = {'exitCode': r.returncode, 'legacy': LEGACY_REL}

    m = STAT_RE.search(out)
    if m:
        cert['counts'] = {
            'sections': int(m.group(1)), 'examples': int(m.group(2)),
            'quizPapers': int(m.group(3)), 'quizQuestions': int(m.group(4)),
            'reviews': int(m.group(5)),
        }
    d = DIFF_RE.search(out)
    if d:
        cert['difficulty'] = {
            'basic': int(d.group(1)), 'basicPct': int(d.group(2)),
            'medium': int(d.group(3)), 'mediumPct': int(d.group(4)),
            'exam': int(d.group(5)), 'examPct': int(d.group(6)),
        }
    b = BI_RE.search(out)
    if b:
        cert['bilingual'] = {
            'boxes': int(b.group(1)), 'pairs': int(b.group(2)),
            'stemEn': int(b.group(3)), 'explainEn': int(b.group(4)),
            'videos': int(b.group(5)),
        }

    issues = [x.strip() for x in ISSUE_RE.findall(out)]
    cert['issues'] = issues
    # 未建章节 / 待建小节只作提示，不算失败（与原脚本同一口径）
    cert['missing'] = _section_list(out, r'未建章节\s*(\d+)\s*个')
    cert['pending'] = _section_list(out, r'待建小节\s*(\d+)\s*个')

    if issues:
        return _triple(False, '发现 %d 个问题：%s' % (len(issues), '；'.join(issues[:3])), cert)
    if r.returncode != 0:
        # 退出码非零但没有解析到 issues：说明输出格式变了，必须报出来，
        # 不能当成「没问题的通过」——那是静默失效。
        return _triple(False, '原脚本退出码 %d，但未解析到问题条目（输出格式可能已变）'
                       % r.returncode, cert)
    return _triple(True, '', cert)


def _section_list(out, header_re):
    """抓「未建章节 / 待建小节」标题后面的 · 列表。"""
    m = re.search(header_re, out)
    if not m:
        return []
    tail = out[m.end():]
    items = []
    for line in tail.split('\n'):
        s = line.strip()
        if s.startswith('·'):
            items.append(s.lstrip('· ').strip())
        elif s and not s.startswith('·'):
            break
    return items


#: 与 checks.py 的 CHECKS 表同形，便于合并到统一报告
CHECKS = [
    ('structure', '结构 / 例题 / 双语统计', parse),
]
