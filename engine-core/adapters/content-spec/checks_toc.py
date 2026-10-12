#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P12 目录↔正文一致（第七十八轮 · **渲染维** ⇒ evidence=render ⇒ env 档 ✓）。

## 判据（**双向** ✓，两类缺陷**分开报** ✓）
① **目录 → 正文**：目录里每条 `href="#id"` 的目标必须**真实存在** ✓（否则红 ✓，证书带目录项 + 目标 id + 页 ✓）；
② **正文 → 目录**：正文里的标题（声明的层级 ✓）**都必须出现在目录里** ✓（否则红 ✓，证书带标题 + 层级 + 位置 ✓）；
- **没有目录**（`hasToc=False`）⇒ **不适用** ✓（不是通过 ✗）；
- **浏览器不在 ⇒ `pass=None` + 环境不足** ✓（退 2 一路 ✓，不是红 ✗）。
声明（容器选择器 / 链接选择器 / 标题选择器 / 层级 / 指向用哪个属性 ✓）全在 manifest ✓，**不硬编码** ✗。
"""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PROBE = os.path.join(REPO, 'apps', 'linalg-lab', 'tools', 'toc-probe.mjs')


def run(artifact, source, base):
    decl = (source.get('toc_coverage') or artifact.get('toc_coverage'))
    if not decl:
        return {'pass': None, 'reason': '不适用：**没有声明"目录与正文标题各指什么"** ✓（未声明 ⇒ 不适用，不是通过 ✗）',
                'certificate': {'needs': 'declaration', 'where': 'manifest.sources[].toc_coverage'}}
    # **路径走引擎自己的 resolve** ✓（产物可能在仓库外 ✓）
    import sys
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    try:
        import common as C, runner as R
        path = C.resolve(artifact, R.BASE)
    except Exception:
        path = os.path.abspath(os.path.join(base, artifact['path']))
    if not os.path.isfile(path):
        return {'pass': None, 'reason': '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）'}
    cmd = ['node', PROBE, 'file://' + path,
           '--toc', decl.get('toc_selector', ''), '--link', decl.get('toc_link_selector', ''),
           '--heading', decl.get('heading_selector', '')]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode == 2:
        why = ((r.stderr or '').strip().splitlines() or ['(无 stderr)'])[-1][:150]
        return {'pass': None, 'reason': '环境不足：目录↔正文（渲染维）这次判不了（不是失败 ✗）｜ 探针 stderr: ' + why,
                'certificate': {'needs': 'browser'}}
    if r.returncode != 0:
        return {'pass': None, 'reason': '检查器故障（探针退出码 %d）：%s' % (r.returncode, (r.stderr or '')[:120]),
                'certificate': {'checker_crash': True}}
    data = json.loads(r.stdout)
    if not data.get('hasToc'):
        return {'pass': None, 'reason': '不适用：这一页**没有目录**（声明的容器选择器一个都没命中 ✓）',
                'certificate': {'hasToc': False, 'toc_selector': decl.get('toc_selector'), 'where': artifact['path']}}
    entries = data.get('entries') or []
    headings = data.get('headings') or []
    levels = set(decl.get('heading_levels') or [2, 3, 4])
    # ① 目录 → 正文
    broken = [e for e in entries if not e.get('exists')]
    if broken:
        e = broken[0]
        return {'pass': False,
                'reason': '① **目录项指向了不存在的标题**：目录文案「%s」→ href="%s"（页内没有这个 id ✓；共 %d 处）'
                          % (e.get('text'), e.get('href'), len(broken)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'render',
                                'detail': {'kind': '① 目录→正文', 'toc_text': e.get('text'), 'href': e.get('href'),
                                           'target_id': e.get('id'), 'count': len(broken),
                                           'where': artifact['path']}}}
    # ② 正文 → 目录
    in_toc = {e.get('id') for e in entries if e.get('id')}
    missing = [h for h in headings if h.get('level') in levels and (h.get('id') or '') not in in_toc]
    if missing:
        h = missing[0]
        return {'pass': False,
                'reason': '② **正文标题未出现在目录里**：<%d> 级标题「%s」（id=%s；位置 top=%s；共 %d 个）'
                          % (h.get('level'), h.get('text'), h.get('id') or '（无 id）', h.get('top'), len(missing)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'render',
                                'environment': {'heading_levels': sorted(levels),
                                                'toc_selector': decl.get('toc_selector')},
                                'detail': {'kind': '② 正文→目录', 'heading': h.get('text'), 'level': h.get('level'),
                                           'id': h.get('id'), 'top': h.get('top'), 'count': len(missing),
                                           'where': artifact['path']}}}
    return {'pass': True, 'reason': '',
            'certificate': {'toc_entries': len(entries), 'headings_checked': len(headings),
                            'two_way': '目录→正文 ✓ / 正文→目录 ✓', 'note': '只判双向一致，不判排序与文案 ✗'}}
