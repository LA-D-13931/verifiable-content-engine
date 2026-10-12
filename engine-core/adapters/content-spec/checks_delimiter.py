#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P6 公式定界符（第六十九轮 · 静态 ⇒ evidence=structural ⇒ repo 档）。

四条子判据分开报，证书带**具体位置与数值** ✓：
① `$` 成对、不跨行（一行内 $ 个数为奇数 ⇒ 红，证书带行号 + 该行原文）；
② `$$` 独占行（去掉定界符后还有非空内容 ⇒ 红）；
③ 行内过长（> 自定阈值 200 字符 ⇒ 红，**阈值来源写明**：本项目现有页面的行内公式长度分布，非外部标准 ✗）；
④ 同一段落里 `$…$` 与 `$$…$$` 混用 ⇒ 红。

⚠️ 必须先剥掉"不算公式的地方"（否则代码密集页刷假红 ✗，照 checks_value.py 的做法 ✓）：
围栏代码块与行内反引号。
"""
import os
import re

INLINE_LIMIT = 200
FENCE = re.compile(r'```.*?```', re.S)
TICK = re.compile(r'`[^`\n]*`')


def strip_code(text):
    """剥掉围栏代码块与行内反引号（行内反引号用等长空格占位，保住行号 ✓）。"""
    kept, i = [], 0
    for m in FENCE.finditer(text):
        kept.append(text[i:m.start()])
        kept.append(' ' * (m.end() - m.start()))
        i = m.end()
    kept.append(text[i:])
    t = ''.join(kept)
    return TICK.sub(lambda m: ' ' * len(m.group(0)), t)


def run(artifact, source, base):
    path = os.path.abspath(os.path.join(base, artifact['path']))
    if not os.path.isfile(path):
        return {'pass': None, 'reason': '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）'}
    raw = open(path, encoding='utf-8').read()
    text = strip_code(raw)
    lines = text.splitlines()

    def dcount(l):
        return l.count('$') - 2 * l.count('$$')

    for k, l in enumerate(lines, 1):
        if l.count('$$'):
            continue
        if dcount(l) % 2 == 1:
            return {'pass': False,
                    'reason': '① 一行内 `$` 个数是奇数（不成对）：第 %d 行｜原文：%s' % (k, l.strip()[:80]),
                    'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                    'detail': {'criterion': '1-成对不跨行', 'line': k, 'text': l.strip()[:120],
                                               'dollar_count': dcount(l), 'where': artifact['path']}}}
    for k, l in enumerate(lines, 1):
        if '$$' in l:
            naked = l.replace('$$', '').strip()
            if naked:
                return {'pass': False,
                        'reason': '② `$$` 没有独占行（该行还有非空内容）：第 %d 行｜原文：%s' % (k, l.strip()[:80]),
                        'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                        'detail': {'criterion': '2-$$独占行', 'line': k, 'text': l.strip()[:120],
                                                   'other_content': naked[:80], 'where': artifact['path']}}}
    for k, l in enumerate(lines, 1):
        for m in re.finditer(r'(?<!\$)\$([^$\n]+)\$(?!\$)', l):
            body = m.group(1)
            if len(body) > INLINE_LIMIT:
                return {'pass': False,
                        'reason': '③ 行内公式过长：长度 %d > 阈值 %d（自定阈值；依据本项目现有页面里行内公式的长度分布，非外部标准）：第 %d 行'
                                  % (len(body), INLINE_LIMIT, k),
                        'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                        'environment': {'threshold': INLINE_LIMIT,
                                                        'threshold_basis': '自定：本项目页面实测分布（非外部标准）'},
                                        'detail': {'criterion': '3-行内过长', 'line': k, 'length': len(body),
                                                   'threshold': INLINE_LIMIT, 'sample': body[:60],
                                                   'where': artifact['path']}}}
    for pi, para in enumerate(re.split(r'\n\s*\n', text), 1):
        if re.search(r'(?<!\$)\$[^$\n]+\$(?!\$)', para) and '$$' in para:
            near = 0
            for k, l in enumerate(lines, 1):
                if l.strip() and l.strip() in para:
                    near = k
                    break
            return {'pass': False,
                    'reason': '④ 同一段落里 `$…$` 与 `$$…$$` 混用：第 %d 段（约第 %d 行）' % (pi, near),
                    'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                    'detail': {'criterion': '4-混用', 'paragraph': pi, 'near_line': near,
                                               'where': artifact['path']}}}
    return {'pass': True, 'reason': '',
            'certificate': {'lines_checked': len(lines), 'inline_limit': INLINE_LIMIT,
                            'code_stripped': bool(FENCE.search(raw) or TICK.search(raw))}}
