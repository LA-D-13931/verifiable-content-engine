#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""人类复核类检查：**把"这需要人看"显式化**，不许混进全绿。

来源是台账 M4：**对自己不擅长的东西下结论**（AI 对图像类内容判断不可靠，却照样给结论）。
那段历史的结局是用户把整个图解全删了。教训不是"别做图"，而是：
**机器判不了的东西，要说"我判不了、请人看"，而不是悄悄给一个绿。**

所以本条检查的产物**永远是「需人复核」**（三态里的 None），它做三件事：
  ① 把该站的"需人复核项"逐条列出来（**在哪、看什么、怎么判**）；
  ② 让套件的汇总里出现"需人工确认 N 条"，任何人扫一眼就知道有多少是机器没签字的；
  ③ 声明 `how_to_check`——**复核也要有判据**，否则"请人看一下"等于没检查。

注意：本检查的 `evidence` 是 `human`，因此**豁免 C2（必须能被反证）**——
它压根不给机器判定，谈不上被证伪；作为交换，它必须声明"人该怎么判"。
"""
from common import triple


def human_review(artifact, source, base):
    items = source.get('human_review') or []
    if not items:
        return triple(None, '本来源没有声明需人复核项（不适用）')
    missing = [i['id'] for i in items if not i.get('how_to_check')]
    if missing:
        return triple(False, '需人复核项缺 how_to_check（"请人看一下"也算检查吗？）：%s'
                      % '、'.join(missing),
                      {'items': len(items)}, advice={'capabilities': [{
                          'capability': 'human-review-contract',
                          'title': '人复核也要有判据',
                          'generalize': '把"我看不准"写成一条检查时，最容易漏的是**复核判据**——'
                                        '于是它退化成一句免责声明。要求写明"看哪、按什么判"。',
                          'fix_hint': '给每条人工项补 how_to_check（在哪看、看什么、什么算过）。',
                      }]})
    cert = {'evidence': 'human', 'items': [{'id': i['id'], 'what': i.get('what', ''),
                                            'how_to_check': i['how_to_check']} for i in items]}
    return triple(None, '需人复核 %d 项（机器不签字）：%s'
                  % (len(items), '；'.join(i['what'] for i in items[:3])), cert)
