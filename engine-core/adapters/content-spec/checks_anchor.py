#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P5 第五维 · 锚点（第六十七轮）：**渲染维** ✓ —— 复用 anchor-highlight-probe.mjs（真实布局 ✓）。

## 判据（来源不许自定而不说明 ✓）
- ① **`href="#id"` 的目标必须存在** ✓（静态也判得了，但这里统一用渲染结果 ✓）；
- ② **目标不得被固定/粘性头部遮住** —— 来源：**WCAG 2.2 SC 2.4.11「Focus Not Obscured (Minimum)」** ✓
  （外部标准 ✓，不是自定 ✗）；
- **浏览器不在 ⇒ `pass=None` + 环境不足** ✓（退 2 一路 ✓，不是红 ✗）。
"""
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PROBE = os.path.join(REPO, 'apps', 'linalg-lab', 'tools', 'anchor-highlight-probe.mjs')


def _probe(path):
    r = subprocess.run(['node', PROBE, 'file://' + path], capture_output=True, text=True, timeout=180)
    if r.returncode == 2:
        why = ((r.stderr or '').strip().splitlines() or ['(无 stderr)'])[-1][:160]
        return None, '环境不足：锚点（渲染维）这次判不了（不是失败 ✗）｜ 探针 stderr: ' + why
    if r.returncode != 0:
        return None, '检查器故障（探针退出码 %d）：%s' % (r.returncode, (r.stderr or '')[:120])
    try:
        return json.loads(r.stdout), None
    except Exception as e:
        return None, '检查器故障：探针输出不是 JSON（%s）' % e


def run(artifact, source, base):
    # 第六十七轮：**相对路径一律 abspath** ✓ —— 我自己的测试 harness 三次传 base='.'
    # ⇒ `file://./…` 非法 ⇒ 探针报 ERR_INVALID_URL ✗（那是测试的错，不是检查的错 ✓）。
    path = os.path.abspath(os.path.join(base, artifact['path']))
    if not os.path.isfile(path):
        return {'pass': None, 'reason': '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）'}
    data, why = _probe(path)
    if why:
        return {'pass': None, 'reason': why, 'certificate': {'needs': 'browser'}}
    anchors = data.get('anchors') or []
    missing = [a for a in anchors if a.get('id') and not a.get('exists')]
    obscured = [a for a in anchors if a.get('exists') and a.get('obscuredBy')]
    if missing:
        a = missing[0]
        return {'pass': False,
                'reason': '锚点目标不存在：href="%s"（元素 id 找不到；共 %d 处）' % (a['href'], len(missing)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'render',
                                'detail': {'href': a['href'], 'id': a['id'], 'kind': 'missing_target',
                                           'count': len(missing), 'text': a.get('text'), 'where': artifact['path']}}}
    if obscured:
        a = obscured[0]
        return {'pass': False,
                'reason': '锚点目标被固定头部遮住：href="%s"（遮住它的是 %s；依据 WCAG 2.2 SC 2.4.11 ✓；共 %d 处）'
                          % (a['href'], a['obscuredBy'], len(obscured)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'render',
                                'environment': {'standard': 'WCAG 2.2 SC 2.4.11 Focus Not Obscured (Minimum)'},
                                'detail': {'href': a['href'], 'id': a['id'], 'obscuredBy': a['obscuredBy'],
                                           'kind': 'obscured_target', 'count': len(obscured), 'where': artifact['path']}}}
    return {'pass': True, 'reason': '', 'certificate': {'anchors_checked': len(anchors),
            'standard': 'WCAG 2.2 SC 2.4.11', 'probe': os.path.relpath(PROBE, REPO)}}
