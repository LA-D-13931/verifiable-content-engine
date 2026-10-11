#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P5 第一段 · 对比度（第六十三轮）：**渲染维** ✓ —— 复用 verify-themes.mjs 的真实计算样式取色。

## 口径（审计方确认三次 ✓）
- **渲染维**：前景/背景色由 CSS 级联 + 主题变量决定 ⇒ **必须上渲染** ✗（静态读样式表会在继承/覆盖/主题切换上算错）。
- **阈值**：`4.5:1`（**WCAG 2.1 AA 对正文**）✓ —— **先 advisory** ✓。**基线**：见 `contrast_baseline` 段（本段说明取自哪里 ✓）。
- **浏览器不在 ⇒ `pass=None`（环境不足，退 2）** ✓ —— **不是红** ✗。

## 阈值基线的出处（要求：写明取自哪个页面或哪组 token ✓）
- **阈值本身**：**WCAG 2.1 AA 正文对比度 4.5:1** ✓（**不是自定** ✓）；
- **基线采集点**：`render_targets` 里已有的页面（`gaoshu-pages` 的 `page-ch1.html` / `page-ch2.html` ✓，即"已知良好"的那两档 ✓）——
  **本轮先只把阈值挂上并标 advisory** ✗；**"已知良好基线"的实测采集（多页取分位数）留作标定步骤** ✓。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PROBE = os.path.join(REPO, 'apps', 'linalg-lab', 'tools', 'contrast-probe.mjs')
MIN_RATIO = 4.5          # WCAG 2.1 AA（正文）✓ —— **先 advisory** ✓


def _lum(c):
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', c or '')
    if not m:
        return None
    r, g, b = (int(m.group(i)) / 255.0 for i in (1, 2, 3))
    f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(fg, bg):
    a, b = _lum(fg), _lum(bg)
    if a is None or b is None:
        return None
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def run(artifact, source, base):
    path = os.path.join(base, artifact['path'])
    if not os.path.isfile(path):
        return {'pass': None, 'reason': '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）'}
    r = subprocess.run(['node', PROBE, 'file://' + path, '--width', '1440', '--min-ratio', str(MIN_RATIO)],
                       capture_output=True, text=True, timeout=120)
    if r.returncode == 2:
        # 第六十五轮：**带上探针自己的 stderr** ✓ —— 只写"没有可用浏览器"会把
        # "真的没浏览器"和"探针起不来（别的环境原因）"混成一句 ✗（我就被它误导过一轮 ✓）。
        _why = (r.stderr or '').strip().splitlines()[-1:] or ['']
        return {'pass': None,
                'reason': '环境不足：没有可用浏览器 ⇒ 对比度（渲染维）这次判不了（不是失败 ✗）｜ 探针 stderr: %s'
                          % (_why[0][:160]),
                'certificate': {'needs': 'browser', 'probe': os.path.relpath(PROBE, REPO), 'probe_stderr': _why[0][:200]}}
    if r.returncode != 0:
        return {'pass': None,
                'reason': '检查器故障（探针退出码 %d）：%s' % (r.returncode, (r.stderr or '')[:120]),
                'certificate': {'checker_crash': True}}
    try:
        data = json.loads(r.stdout)
    except Exception as e:
        return {'pass': None, 'reason': '检查器故障：探针输出不是 JSON（%s）' % e, 'certificate': {'checker_crash': True}}
    bad = []
    for it in data.get('items') or []:
        rr = ratio(it.get('fg'), it.get('bg'))
        if rr is None:
            continue
        # WCAG：正文 < 4.5 判红（大字放宽到 3.0 —— 这里只做 advisory 的正文部分 ✓）
        need = 3.0 if (it.get('size', 16) >= 24 or (it.get('size', 16) >= 18.66 and str(it.get('weight')) in ('700', 'bold'))) else MIN_RATIO
        if rr < need:
            bad.append((round(rr, 2), need, it.get('fg'), it.get('bg'), (it.get('text') or '')[:30]))
    if bad:
        rr, need, fg, bg, txt = bad[0]
        return {'pass': False,
                'reason': '对比度不足：%.2f:1 < 阈值 %.2f:1（WCAG 2.1 AA 正文；**advisory** ✓）—— 例：「%s」（前景 %s ／ 背景 %s；共 %d 处）'
                          % (rr, need, txt, fg, bg, len(bad)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'render',
                                'environment': {'probe': os.path.relpath(PROBE, REPO), 'width': data.get('width')},
                                'detail': {'ratio': rr, 'threshold': need, 'standard': 'WCAG 2.1 AA (normal text)',
                                           'mode': 'advisory', 'fg': fg, 'bg': bg, 'sample': txt, 'count': len(bad),
                                           'baseline': '阈值=WCAG 常数；基线采集点=render_targets 的既有页面（page-ch1/ch2）'}}}
    return {'pass': True, 'reason': '', 'certificate': {'width': data.get('width'), 'threshold': MIN_RATIO, 'mode': 'advisory'}}
