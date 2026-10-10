#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""回归类检查：**体量回退对照**。

治的是台账里最致命的一类（M6：改一处、坏另一处，且没有对照）：
曾经"正文被删掉一段"而静态校验全过；也曾一次把 **369 个渲染容器打成 204 个**，
靠"回退到旧版跑同一测量"才发现。

判据：把关键计数存进**基线文件**，每次回归重新测一遍并比对，**骤降即报**。
这是本域第一条**有状态**的检查——它的依据不是产物本身，而是"产物与上次相比"，
所以基线必须由 `runner.py --baseline` **显式重算**（不许顺手改）。

度量函数 `metrics()` 是本文件唯一实现：基线生成与回归比对都用它，
否则"基线记的口径"和"回归量的口径"会各说各话（本项目最忌的第二份实现）。
"""
import json
import os
import re

from common import resolve, triple

METRICS_FILE = 'baseline.json'


def metrics(html):
    """三个关键计数。口径固定在这里，别处不许再算一套。"""
    stripped = re.sub(r'<(script|style)\b.*?</\1>', ' ', html, flags=re.S | re.I)
    visible = re.sub(r'<[^>]+>', '', stripped)
    return {
        'text_chars': len(''.join(visible.split())),
        'elements': len(re.findall(r'<[a-zA-Z][\w-]*', html)),
        'paragraphs': len(re.findall(r'<p\b', stripped)),
    }


def load_baseline(base):
    p = os.path.join(base, METRICS_FILE)
    if not os.path.isfile(p):
        return None
    with open(p, encoding='utf-8') as f:
        return json.load(f)


def content_volume_regression(artifact, source, base):
    """与基线比对：可见文本量骤降即报。

    产物可用 `baseline_from` 继承另一个产物的基线（用于突变体：
    突变体的基线应当是**未突变前**那一份的计数）。
    """
    base_data = load_baseline(base)
    if base_data is None:
        return triple(None, '没有基线文件（跑 runner.py --baseline 生成后再用）')
    key = artifact.get('baseline_from') or artifact['id']
    prev = (base_data.get('artifacts') or {}).get(key)
    if prev is None:
        return triple(None, '该产物没有基线记录（%s）—— 本项不适用' % key)

    path = resolve(artifact, base)
    if not os.path.isfile(path):
        return triple(False, '产物不存在，但基线里有它：%s（文件被删了？）' % artifact['path'],
                      {'baseline': prev, 'current': None, 'missing': True})
    with open(path, encoding='utf-8', errors='replace') as f:
        now = metrics(f.read())
    cfg = source.get('volume_baseline') or {}
    max_pct = cfg.get('max_drop_pct', 1.0)
    max_chars = cfg.get('max_drop_chars', 300)

    drops = []
    for k, prev_v in prev.items():
        cur = now.get(k, 0)
        allowed = max(max_chars, prev_v * max_pct / 100.0)
        if prev_v - cur > allowed:
            drops.append({'metric': k, 'before': prev_v, 'after': cur,
                          'drop': prev_v - cur, 'allowed': round(allowed)})
    cert = {'baseline_from': key, 'before': prev, 'now': now, 'drops': drops,
            'thresholds': {'max_drop_pct': max_pct, 'max_drop_chars': max_chars}}
    if drops:
        d = drops[0]
        return triple(False,
                      '%d 项计数回退：%s 从 %d 降到 %d（少了 %d，阈值 %d）'
                      % (len(drops), d['metric'], d['before'], d['after'], d['drop'], d['allowed']),
                      cert,
                      advice={'capabilities': [{
                          'capability': 'content-volume-regression',
                          'title': '体量回退',
                          'generalize': '改动会静默吃掉内容：删掉一段、模板把容器数量砍半、'
                                        '构建漏掉一个文件——它们都不报错，只是东西少了。'
                                        '有基线才知道"少了"。',
                          'fix_hint': '先 diff 与上一次的产物，确认是有意精简还是误删；'
                                      '若是有意精简，用 runner.py --baseline 显式更新基线（不要手改）。',
                      }]})
    return triple(True, '', cert)
