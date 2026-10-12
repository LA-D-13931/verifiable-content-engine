#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P13 来源声明（第七十五轮 · **静态** ⇒ evidence=structural）。

## 口径（照台账与审计方给的 ✓）
台账 P13：**每章必须有来源声明字段，缺即报** ✓。
**只验"声明在不在"，验不了真假** ✓ —— 但"有没有"是**二值的、可判的** ✓，正是这一条要的 ✓。

## 格式从哪来（不硬编码 ✓）
**声明在 manifest**：`sources[].provenance_disclosure.markers` ✓（本项目一路的做法：条文声明进 manifest ✓）。
页里命中**任一**标记即算"有声明" ✓；一个都没命中 ⇒ **红** ✓（证书带**产物 id** + **缺哪个字段/试过哪些标记** ✓）。
"""
import os
import sys

# **路径一律走引擎自己的 resolve** ✓（第六十九轮纪律：产物可能在**仓库外**，如高数站 17 章 ✓）——
# 我第一版用 os.path.join(base, …) ✗ ⇒ 17 章全判"不在位" ✗（这个病又犯了一次 ✓）。
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:
    import common as _common
    import runner as _runner
except Exception:            # 直接调本模块时的兜底 ✓
    _common = _runner = None


def run(artifact, source, base):
    decl = (source.get('provenance_disclosure') or artifact.get('provenance_disclosure'))
    if not decl:
        return {'pass': None,
                'reason': '不适用：**没有声明"来源声明长什么样"**（未声明 ⇒ 不适用 ✓，不是通过 ✗）',
                'certificate': {'needs': 'declaration', 'where': 'manifest.sources[].provenance_disclosure'}}
    markers = decl.get('markers') or []
    if not markers:
        return {'pass': None, 'reason': '不适用/环境不足：声明的标记列表是空的 ⇒ 无法判定 ✓',
                'certificate': {'needs': 'markers'}}
    if _common is not None and _runner is not None:
        path = _common.resolve(artifact, _runner.BASE)      # **与 runner 同源** ✓
    else:
        path = os.path.abspath(os.path.join(base, artifact['path']))
    if not os.path.isfile(path):
        return {'pass': None, 'reason': '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）'}
    text = open(path, encoding='utf-8', errors='ignore').read()
    for m in markers:
        if m in text:
            return {'pass': True, 'reason': '',
                    'certificate': {'matched_marker': m, 'per': decl.get('per'),
                                    'requirement': decl.get('requirement'),
                                    'note': '只验在不在，不验真假 ✓'}}
    return {'pass': False,
            'reason': '本页**没有来源声明字段**（台账 P13：每章必须有 ✓）—— 试过 %d 个声明标记，一个都没命中' % len(markers),
            'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                            'detail': {'artifact': artifact['id'], 'missing_field': decl.get('requirement'),
                                       'tried_markers': markers, 'per': decl.get('per'),
                                       'where': artifact['path']}}}
