#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编号契约检查：编号必须**唯一、页内连续、且前缀与所在文件一致**。

来源：外部调研把"题号／题目／答案错位"列为**高严重度·常见**（2.4）——
"第 3 题答案写的是第 5 题的解析"在教学场景几乎等同于答案错误。
根因是多 Agent 各自生成题目与解答却**没有统一编号契约**。

与 `answer-key` 的分工：`answer-key` 管"✓ 标记 ↔ correct 字段"，
本检查管"**编号本身**"——两者合起来才是完整的编号契约。

判据全部来自 manifest 声明（不猜）：
  · `claim_pattern`  —— 从产物里取出编号的写法（如 `data-quiz-id="..."`）
  · `shape`          —— 编号的形状（分组：`^(ch(\\d+))-(\\d+)$`）
  · `prefix_from_file` —— 从文件名推出**期望前缀**（如 `^ch(\\d+)`）
"""
import os
import re

from common import resolve, triple


def _read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def numbering_contract(artifact, source, base):
    spec = source.get('numbering')
    if not spec:
        return triple(None, '本来源没有声明编号契约（不适用）')
    path = resolve(artifact, base)
    if not os.path.isfile(path):
        return triple(False, '找不到产物 %s' % artifact['path'])
    text = _read(path)
    ids = re.findall(spec['claim_pattern'], text)
    if not ids:
        return triple(None, '产物里没有出现声明的编号字段（%s）—— 本项不适用'
                      % spec['claim_pattern'][:40], {'ids': 0})

    shape = re.compile(spec['shape'])
    problems, cert = [], {'count': len(ids)}
    # ① 唯一
    dup = sorted({i for i in ids if ids.count(i) > 1})
    cert['duplicate'] = dup
    if dup:
        problems.append('编号重复：%s' % '、'.join(dup[:5]))
    # ② 页内连续（按形状的最后一个分组）
    shaped = {}
    for i in ids:
        m = shape.match(i)
        if not m:
            # 合法例外必须在 manifest 声明（如章末总测 `ch1-final`）：不猜意图、但允许声明
            if any(re.search(pat, i) for pat in (spec.get('shape_exceptions') or [])):
                cert.setdefault('exceptions_seen', []).append(i)
                continue
            problems.append('编号形状不符：%s（期望 %s）' % (i, spec['shape']))
            continue
        shaped.setdefault(m.group(1), []).append(int(m.groups()[-1]))
    cert['groups'] = {k: sorted(v) for k, v in shaped.items()}
    if spec.get('require_continuous', True):
        for prefix, nums in shaped.items():
            if sorted(nums) != list(range(1, len(nums) + 1)):
                problems.append('%s 组编号不连续：%s' % (prefix, sorted(nums)[:8]))
    # ③ 前缀必须与所在文件一致
    if spec.get('prefix_from_file'):
        m = re.match(spec['prefix_from_file'], os.path.basename(path))
        if m:
            want = m.group(1)
            wrong = sorted({k for k in shaped if k != want})
            cert['expected_prefix'] = want
            if wrong:
                problems.append('编号前缀与文件不符：文件是 %s，却出现 %s' % (want, wrong[:4]))

    if problems:
        return triple(False, '编号契约 %d 处不符：%s' % (len(problems), '；'.join(problems[:3])), cert,
                      advice={'capabilities': [{
                          'capability': 'numbering-contract',
                          'title': '编号契约',
                          'generalize': '凡"编号 + 内容"分头生成的地方都会错位：题号与解析、目录与正文、'
                                        '图号与图注、章节序号与锚点。编号必须唯一、连续、且与所在容器一致。',
                          'fix_hint': '把编号视为**契约字段**（唯一来源生成），而不是各处手写；'
                                      '本站已有 tools/check-numbering.py 可作参照实现。',
                      }]})
    return triple(True, '', cert)
