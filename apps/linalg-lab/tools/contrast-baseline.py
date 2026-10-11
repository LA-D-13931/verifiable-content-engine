#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比度基线采集（第六十五轮 P5 第三件）：在**真实产物**上取分位数 ✓。

用法：python3 tools/contrast-baseline.py <产物1> [产物2 …]
输出：每个文件的比值分位数（min / p10 / p50 / max）+ 全体的分位数 ✓（写进需求登记的 evidence ✓）
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROBE = os.path.join(HERE, 'contrast-probe.mjs')
# HERE = <repo>/apps/linalg-lab/tools ⇒ 往上是 <repo> ✓
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, 'engine-core', 'adapters', 'content-spec'))
import checks_contrast as C          # 复用同一个比值实现（单一来源 ✓）


def ratios(path):
    r = subprocess.run(['node', PROBE, 'file://' + os.path.abspath(path)], capture_output=True, text=True, timeout=180)
    if r.returncode == 2:
        return None
    data = json.loads(r.stdout)
    out = []
    for it in data.get('items') or []:
        v = C.ratio(it.get('fg'), it.get('bg'))
        if v is not None:
            out.append(round(v, 2))
    return out


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = max(0, min(len(xs) - 1, int(round((p / 100.0) * (len(xs) - 1)))))
    return xs[k]


def main():
    files = sys.argv[1:]
    allv = []
    per = {}
    for f in files:
        v = ratios(f)
        if v is None:
            print('  – %s：环境不足（浏览器不在）' % os.path.basename(f)); continue
        if not v:
            print('  – %s：没有可测文本（跳过 ✓）' % os.path.basename(f)); continue
        per[os.path.basename(f)] = {'n': len(v), 'min': min(v), 'p10': q(v, 10), 'p50': q(v, 50), 'max': max(v)}
        allv += v
        print('  %-24s n=%-4d min=%-6s p10=%-6s p50=%-6s max=%s' % (os.path.basename(f), len(v), min(v), q(v, 10), q(v, 50), max(v)))
    print('\n  **全体**：n=%d ｜ min=%s ｜ p10=%s ｜ p50=%s ｜ p90=%s ｜ max=%s'
          % (len(allv), min(allv) if allv else '-', q(allv, 10), q(allv, 50), q(allv, 90), max(allv) if allv else '-'))
    print(json.dumps({'per_file': per, 'overall': {'n': len(allv), 'min': min(allv) if allv else None,
          'p10': q(allv, 10), 'p50': q(allv, 50), 'p90': q(allv, 90), 'max': max(allv) if allv else None}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
