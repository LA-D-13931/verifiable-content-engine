#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P9 KaTeX 命令白名单（第六十一轮）。

## 依据与出处
白名单是**仓库内的声明文件** `fixtures/katex-allowlist.json` ✓，其中写明
`source / version / fetched / 抽取方式 / coverage` ✓ —— **出处与覆盖范围都在文件里** ✓。

## 判据
- 定界符内出现的 `\\cmd`：
  - 在 `whitelist` 里 ⇒ **通过** ✓；
  - 在 `not_supported` 里（官方逐字标 "Not supported"）⇒ **红** ✓；
  - **不在白名单** ⇒ **红** ✓（**这条是关键** ✓：不是"只认得几个常见命令"✗）；
- **白名单为空（或文件缺失）⇒ `pass=None`（环境不足）** ✓ —— **不许在空集上"全部通过"** ✗（P12 的假绿 ✓）。
"""
import json
import os
import re

CMD = re.compile(r'\\([A-Za-z]+)')
ALLOW = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'katex-allowlist.json')


def run(artifact, source, base):
    try:
        payload = json.load(open(ALLOW, encoding='utf-8'))
    except Exception as e:
        return {'pass': None, 'reason': '环境不足：白名单文件读不到（%s）' % e,
                'certificate': {'allowlist': ALLOW, 'ok': False}}
    wl = set(payload.get('whitelist') or [])
    if not wl:
        return {'pass': None, 'reason': '环境不足：白名单是空的 ⇒ 无法判定（空集上不许报通过 ✗）',
                'certificate': {'allowlist': ALLOW, 'size': 0, 'source': payload.get('source')}}
    path = os.path.join(base, artifact['path'])
    if not os.path.isfile(path):
        return {'pass': None, 'reason': '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）'}
    text = open(path, encoding='utf-8').read()
    # 只看数学定界符内（$…$ / $$…$$ / \\(…\\) / \\[…\\]）
    spans = re.findall(r'\$\$(.+?)\$\$|\$(.+?)\$|\\\((.+?)\\\)|\\\[(.+?)\\\]', text, flags=re.S)
    body = '\n'.join(x for t in spans for x in t if x)
    bad, unsup = [], []
    for m in CMD.finditer(body):
        c = '\\' + m.group(1)
        if c in payload.get('not_supported', []):
            unsup.append(c)
        elif c not in wl:
            bad.append(c)
    if unsup:
        c = unsup[0]
        return {'pass': False,
                'reason': 'KaTeX **不支持**该命令：%s（官方 support_table 逐字标 "Not supported"；共 %d 处）'
                          % (c, len(unsup)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                'environment': {'allowlist_version': payload.get('version')},
                                'detail': {'command': c, 'kind': 'not_supported',
                                           'count': len(unsup), 'where': artifact['path'],
                                           'source': payload.get('source')}}}
    if bad:
        c = bad[0]
        return {'pass': False,
                'reason': '命令**不在白名单内**：%s（共 %d 处；白名单 %d 条，出处见声明文件；'
                          '**覆盖范围是 partial** ⇒ 若该命令其实受支持，请补进白名单并给出处 ✓）'
                          % (c, len(bad), len(wl)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                'environment': {'allowlist_version': payload.get('version')},
                                'detail': {'command': c, 'kind': 'not_in_whitelist',
                                           'count': len(bad), 'where': artifact['path'],
                                           'coverage': payload.get('coverage')}}}
    return {'pass': True, 'reason': '',
            'certificate': {'checked_in_delimiters': bool(body), 'allowlist_size': len(wl)}}
