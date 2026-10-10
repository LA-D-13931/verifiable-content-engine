#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数据级检查：**答案键 ↔ 解析一致**。

这条是用户台账里点名的缺陷（"答案键与解析不一致 → 要求寻找软件中所有类似问题并重修"）。
判据（与参考实现 `apps/linalg-lab/tools/check-lab.py` 同源，那一条已跑在 58 个真实任务上）：
  · 每题的 `explains` 里**恰好有一个**以 ✓ 开头，且它的下标 == `correct`；
  · `correct` 是整数且在下标范围内；
  · `options` 与 `explains` 数量一致。

这条检查的夹具里有**突变体**：`foundation-index.mutant.json` 是把一道题的 `correct`
位移一位造出来的（声明式突变，不是抄来的真实坏例）。真实数据本身 0 处不一致，
所以不靠突变体就无法反证这条检查——突变体是这类"现状全好"的检查唯一能自证的方式。
"""
import json
import os
import re

from common import triple




def _collect(obj, out):
    if isinstance(obj, dict):
        if isinstance(obj.get('options'), list) and ('correct' in obj or 'explains' in obj):
            out.append(obj)
        for v in obj.values():
            _collect(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect(v, out)


def answer_key(artifact, source, base):
    path = os.path.join(base, artifact['path'])
    if not os.path.isfile(path):
        return triple(False, '找不到数据文件 %s' % artifact['path'])
    try:
        data = json.load(open(path, encoding='utf-8'))
    except Exception as e:
        return triple(False, '数据不是合法 JSON：%s' % str(e)[:60])

    questions = []
    _collect(data, questions)
    if not questions:
        return triple(False, '没有扫到任何题目（判据与数据形状不符？）')

    problems, stats = [], {'questions': len(questions), 'affirmed_exactly_one': 0}
    for i, q in enumerate(questions, 1):
        opts, exps, correct = q.get('options'), q.get('explains'), q.get('correct')
        tag = '第 %d 题' % i
        if not isinstance(correct, int) or not isinstance(opts, list) or not (0 <= correct < len(opts)):
            problems.append('%s 的 correct 非法或越界：%r' % (tag, correct))
            continue
        if not isinstance(exps, list):
            problems.append('%s 没有 explains' % tag)
            continue
        if len(opts) != len(exps):
            problems.append('%s 选项数(%d) 与解析数(%d) 不一致' % (tag, len(opts), len(exps)))
        affirmed = [j for j, e in enumerate(exps) if str(e).strip().startswith('✓')]
        if affirmed == [correct]:
            stats['affirmed_exactly_one'] += 1
        else:
            problems.append('%s 打 ✓ 的下标 %s 与 correct %d 不一致（应恰好是 [%d]）'
                            % (tag, affirmed or '无', correct, correct))

    cert = {'questions': stats['questions'], 'affirmed_exactly_one': stats['affirmed_exactly_one'],
            'problems': problems[:8]}
    if problems:
        return triple(False, '%d/%d 题答案键与解析不一致：%s'
                       % (len(problems), len(questions), '；'.join(problems[:3])), cert,
                       advice={'capabilities': [{
                           'capability': 'answer-key',
                           'title': '答案键 ↔ 解析一致',
                           'generalize': '只要有"一处声明正确答案、另一处用文字标出对错"的地方就会漂移：'
                                         '题干/选项/解析/答案键、双语两栏、正解与讲评。'
                                         '判据是"✅ 标记的集合必须恰好等于答案键"。',
                           'fix_hint': '改数据里的 correct，或改对应解析的 ✓ 标记——两者必须同时成立；'
                                       '参考实现见 apps/linalg-lab/tools/check-lab.py 的 check_choice_uniqueness',
                       }]})
    return triple(True, '', cert)
