#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P5 第三段 · 间距（第六十六轮 · **静态可判** ✓）。

## 口径（判据来源不许自定而不说明 ✓）
- **尺度来源**：`fixtures/spacing-scale.json`（**声明文件** ✓）—— 记 `source`（哪里来的）+ `scale`（允许的档位 ✓）；
- **判据**：静态样式里的间距值（`margin*/padding*/gap/row-gap/column-gap` 的 px 值 ✓）
  **必须命中允许档位**（含 0 ✓）✓；**非 0 且不在档位内 ⇒ 红** ✓；
- **为什么是静态** ✓：间距是"**声明出来的数**" ✓（不依赖布局/渲染 ✓）—— 与对比度（渲染维 ✓）不同 ✓；
- **写法检查**：`style="..."` 内联 + `<style>` 块内的声明 ✓（**不解析外部 CSS 文件** ✗：本轮如实写进 docstring ✓）。
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SCALE_FILE = os.path.join(HERE, 'fixtures', 'spacing-scale.json')
PROPS = ('margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
         'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
         'gap', 'row-gap', 'column-gap')
DECL = re.compile(r'([a-z-]+)\s*:\s*([^;"\n}]+)', re.I)
PX = re.compile(r'(-?\d+(?:\.\d+)?)px')


def run(artifact, source, base):
    try:
        cfg = json.load(open(SCALE_FILE, encoding='utf-8'))
        scale = set(float(x) for x in (cfg.get('scale') or []))
    except Exception as e:
        return {'pass': None, 'reason': '环境不足：间距尺度声明读不到（%s）' % e,
                'certificate': {'scale_file': SCALE_FILE}}
    if not scale:
        return {'pass': None, 'reason': '环境不足：间距尺度是空的 ⇒ 无法判定（**空集上不许报通过** ✗）',
                'certificate': {'scale_file': SCALE_FILE, 'size': 0, 'source': cfg.get('source')}}
    path = os.path.join(base, artifact['path'])
    if not os.path.isfile(path):
        return {'pass': None, 'reason': '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）'}
    text = open(path, encoding='utf-8').read()
    bad = []
    for m in DECL.finditer(text):
        prop, val = m.group(1).lower(), m.group(2)
        if prop not in PROPS:
            continue
        for pm in PX.finditer(val):
            v = float(pm.group(1))
            if v != 0 and v not in scale:
                bad.append((prop, v))
    if bad:
        prop, v = bad[0]
        return {'pass': False,
                'reason': '间距不在声明的尺度里：%s = %spx（尺度 %s；共 %d 处）'
                          % (prop, v, sorted(scale)[:8], len(bad)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                'environment': {'scale_source': cfg.get('source')},
                                'detail': {'property': prop, 'value_px': v, 'scale': sorted(scale),
                                           'count': len(bad), 'where': artifact['path']}}}
    return {'pass': True, 'reason': '',
            'certificate': {'scale': sorted(scale), 'source': cfg.get('source'), 'checked': len(PROPS)}}
