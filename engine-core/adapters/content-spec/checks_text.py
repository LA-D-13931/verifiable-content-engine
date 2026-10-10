#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文本类检查：**邻近重复段落**（生成故障，不是"内容复现"）。

## 这条检查的判据是**被一次负结果逼出来的**

第一版判据是"同页重复段落"——在真实站点上量出 **12/12 页共 325 段"重复"**，
逐条看**全是 `$$…$$` 公式段**。数学教材里公式复现是**合法的**：
同一个公式在定理、证明、例题里各出现一次很正常。照第一版实现会假阳性 325 处
（这就是台账 M5「检测器没校准就拿来判断」的又一个实例）。

四条修正条件（同时满足才算）：
  ① **只认散文**——必须含中文、且不含 `$` / `\\`（排除公式段）；
  ② **长度 ≥ 60 字**（短句重复是正常修辞）；
  ③ **邻近**——两次出现在 20000 字符以内（生成故障通常成片出现；
     远距离复现是"呼应"，不是故障）；
  ④ 允许**声明**样板重复（`allowed_repeats`）：页脚、免责声明这类合法重复。

按这四条在真实站点上重测：**0 处**。所以本检查的反例只能来自**突变体**——
把一段散文原样复制到附近，它必须被抓到。
"""
import os
import re

from common import resolve, triple

CJK = re.compile(r'[\u4e00-\u9fff]')


def _prose_paragraphs(html):
    """返回 [(位置, 文本)]：散文段落（排除 script/style、公式、短句）。"""
    txt = re.sub(r'<(script|style)\b.*?</\1>', ' ', html, flags=re.S | re.I)
    out = []
    for m in re.finditer(r'<p\b[^>]*>(.*?)</p>', txt, re.S):
        body = ' '.join(re.sub(r'<[^>]+>', '', m.group(1)).split())
        out.append((m.start(), body))
    return out


def dup_block(artifact, source, base):
    spec = source.get('dup_block') or {}
    min_len = spec.get('min_chars', 60)
    window = spec.get('window_chars', 20000)
    allowed = set(spec.get('allowed_repeats') or [])
    path = resolve(artifact, base)
    if not os.path.isfile(path):
        return triple(False, '找不到产物 %s' % artifact['path'])
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()

    seen, hits, checked = {}, [], 0
    for pos, body in _prose_paragraphs(html):
        if len(body) < min_len or not CJK.search(body):
            continue
        if '$' in body or '\\' in body:          # 条件①：排除公式
            continue
        if body in allowed:                      # 条件④：声明的样板重复
            continue
        checked += 1
        prev = seen.get(body)
        if prev is not None and pos - prev <= window:   # 条件③：邻近
            hits.append({'first': prev, 'again': pos, 'text': body[:60]})
        seen.setdefault(body, pos)

    cert = {'prose_paragraphs_checked': checked, 'min_chars': min_len,
            'window_chars': window, 'allowed_repeats': sorted(allowed),
            'duplicates': hits[:6]}
    if checked == 0:
        return triple(None, '静态标记里没有可比对的散文段落（DOM 可能由运行时生成）—— 本项不适用', cert)
    if hits:
        h = hits[0]
        return triple(False, '邻近重复 %d 处：同一段散文在 %d 字符内出现两次（如「%s…」）'
                      % (len(hits), window, h['text']),
                      cert, advice={'capabilities': [{
                          'capability': 'dup-block',
                          'title': '邻近重复段落',
                          'generalize': '生成类工具的典型故障是**成片重复**：同一段话在附近出现两次。'
                                        '判据必须排除公式（公式复现是合法的）、只看散文、且要求邻近。',
                          'fix_hint': '删掉后一处重复，或把两处合并；若是合法的样板文字，'
                                      '把它加进 manifest 的 allowed_repeats。',
                      }]})
    return triple(True, '', cert)
