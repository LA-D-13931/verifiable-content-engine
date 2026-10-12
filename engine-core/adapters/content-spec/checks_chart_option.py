#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P10 图表配置出处（第七十七轮 · **静态** ⇒ evidence=structural ⇒ repo 档）。

## 台账原话
「图表配置必须由**声明的脚本/数据**产出（不是手写 option），且可校验；**手写字面配置即报**」✓

## 只判什么（与 P4/P13 同一纪律 ✓）
**只判"声明在不在 / 是不是手写字面量"** ✓ —— **不判"声明真假"** ✓（那需要跑脚本 ✓，属另一条路 ✓）。

## 声明从哪来（不硬编码 ✓）
`manifest.sources[].chart_option_provenance` ✓：`declaration_markers`（声明式产出的标记 ✓）＋ `forbidden_markers`（手写字面量的形态 ✓）。
判定：命中 **forbidden** 且**没有**命中 **declaration** ⇒ **红** ✓（证书带产物 id + 命中的手写形态 + 行号 ✓）；
命中 declaration ⇒ 绿 ✓；两者都没命中 ⇒ **不适用**（这一页没有图表 ✓，不是通过 ✗）。
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:
    import common as _common
    import runner as _runner
except Exception:
    _common = _runner = None


def run(artifact, source, base):
    decl = (source.get('chart_option_provenance') or artifact.get('chart_option_provenance'))
    if not decl:
        return {'pass': None, 'reason': '不适用：**没有声明"图表配置该由什么产出"** ✓（未声明 ⇒ 不适用，不是通过 ✗）',
                'certificate': {'needs': 'declaration', 'where': 'manifest.sources[].chart_option_provenance'}}
    dm = decl.get('declaration_markers') or []
    fm = decl.get('forbidden_markers') or []
    if not fm:
        return {'pass': None, 'reason': '不适用/环境不足：声明的"手写形态"列表为空 ⇒ 无法判定 ✓',
                'certificate': {'needs': 'forbidden_markers'}}
    # **路径一律走引擎自己的 resolve** ✓（产物可能在仓库外 ✓）
    if _common is not None and _runner is not None:
        path = _common.resolve(artifact, _runner.BASE)
    else:
        path = os.path.abspath(os.path.join(base, artifact['path']))
    if not os.path.isfile(path):
        return {'pass': None, 'reason': '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）'}
    text = open(path, encoding='utf-8', errors='ignore').read()
    hit_d = next((m for m in dm if m in text), None)
    hits = []
    for m in fm:
        start = 0
        while True:
            i = text.find(m, start)
            if i < 0:
                break
            hits.append({'marker': m, 'line': text.count('\n', 0, i) + 1})
            start = i + len(m)
    has_chart = bool(hits) or bool(hit_d)
    if not has_chart:
        return {'pass': None, 'reason': '不适用：这一页没有图表（既没命中"手写形态"，也没命中"声明式标记"）✓',
                'certificate': {'no_chart': True, 'where': artifact['path']}}
    if hits and not hit_d:
        return {'pass': False,
                'reason': '图表配置是**手写字面量**（台账 P10 要求由声明的脚本/数据产出 ✓）：命中「%s」于第 %d 行（共 %d 处），且本页没有任何声明式标记' % (hits[0]['marker'], hits[0]['line'], len(hits)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                'detail': {'artifact': artifact['id'], 'handwritten_hits': hits[:5],
                                           'declaration_markers_tried': dm, 'where': artifact['path']}}}
    return {'pass': True, 'reason': '',
            'certificate': {'matched_declaration': hit_d, 'requirement': decl.get('requirement'),
                            'note': '只判声明在不在 / 是不是手写字面量，不判声明真假 ✓'}}
