#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P3 数值出处（第四十三轮）：**只查「数量陈述」**。

## 口径（审计方 §1.1 定死，防误报爆炸）
**只查"后面跟着量词的那些数字"**：`N 个 / N 项 / N 条 / N 处 / N 章 / N 节 / N 题 / N 组 / N 类 / N 次 / N 份` ✓。
**页码、章节号、日期、题号、公式里的数不进范围** ✗ —— 它们本来就不该有出处 ✓
（对所有数字都要求溯源 ⇒ 真实语料上误报爆炸 ⇒ 检查会被立刻关掉 ✓）。

## 判据（§1.3）
- 数字 + 同一量词能在**声明的来源**（`source['value_sources']` 里的数据源文件 / 生成脚本）里找到 → **通过** ✓；
- 找不到 → **报红** ✓，证书带 `{'number': N, 'unit': '个', 'where': '…', 'declared_sources': [...]}` ✓；
- 该源**没声明** `value_sources` → **判「不适用」**（`pass=None` ✓ 三态纪律：不是通过、也不是失败 ✓）。
"""
import os
import re

#: 「数量陈述」：数字 + 量词（**这张表就是本检查的查什么/不查什么**）
#: **不查**的结构引用（第五十轮：用证书原文定的规则 ✓）——「第 N 章」「§1-1 节」「见 §N 节」「参考第 N 章」
STRUCT_REF = ('第', '§', '见', '参考', '详见')

#: **不查**的行文（第四十六轮抽查结论）：比喻/量级比较/数学陈述里的"个"不是"数量陈述" ✗
#  —— 逐字证据：「松 5 个数量级」「概率向量只有 1 个分量」都不是"数了 N 个东西" ✓
STOP_PHRASES = ('数量级', '个分量', '个维度', '个元素', '个样本')

QUANTITY = re.compile(r'(?<![\d.])(\d{1,4})\s*(个|项|条|处|章|节|题|组|类|次|份)')


def claim_at(text, m):
    """**口径的唯一实现**（第五十一轮抽取）：某处命中是否算"要找来源的数量陈述"。

    返回 (是否算, 排除原因)。**检查与分类脚本都必须调它** ——
    否则两边各写一份规则，就会出现"131 与 ①+④ 差 11 处"那种对不上的账 ✗。

    排除规则（每条都由抽样原文定 ✓）：
    - `STOP_PHRASES`：行文比喻/量级比较（"松 5 个数量级"、"1 个分量"）；
    - `STRUCT_REF`：结构引用（"第 1 章"、"§1-1 节"、"见 §N"、"参考第 N 章"）；
    - 代码块内的数字（调用方先剥）。
    """
    n, unit = m.group(1), m.group(2)
    seg = text[max(0, m.start() - 20):m.end() + 6]
    pre = text[max(0, m.start() - 22):m.start()]
    if any(sp in seg for sp in STOP_PHRASES):
        return False, 'STOP_PHRASES'
    if any(w in pre for w in STRUCT_REF):
        return False, 'STRUCT_REF'
    if re.search(r'^(CHAPTER|Ch\.?)\s*$', text[max(0, m.start() - 10):m.start()].strip()):
        return False, 'CHAPTER'
    return True, ''

def run(artifact, source, base):
    srcs = source.get('value_sources')
    if not srcs:
        return {'pass': None,
                'reason': '本来源未声明数值出处（value_sources），数量陈述的溯源不适用',
                'certificate': {'declared_value_sources': None}}
    # **用引擎自己的 resolve**（第四十七轮：我原来自己拼路径 ⇒ 对页面报「找不到产物」✗，
    # 而 common.resolve 明明找得到 —— 正是 循环纪律.md 第 1 条那一族 ✗）
    import common
    path = common.resolve(artifact, base)

    if not os.path.isfile(path):
        return {'pass': None, 'reason': '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）'}
    text = open(path, encoding='utf-8').read()
    # 剥掉代码块 / 行内代码（代码里的数字不是"数量陈述" ✓）
    text_wo_code = re.sub(r'```.*?```', '', text, flags=re.S)
    text_wo_code = re.sub(r'`[^`]*`', '', text_wo_code)
    # 汇总声明的来源里出现的「数字+量词」
    pool = []
    for s in srcs:
        sp = common.resolve({'path': s}, base)
        if os.path.isfile(sp):
            pool.append(open(sp, encoding='utf-8').read())
    pool = '\n'.join(pool)
    missing = []
    hits = []                       # 每处命中的**原文**（第四十九轮：证书不许只给 number/unit ✗）
    for m in QUANTITY.finditer(text_wo_code):
        n, unit = m.group(1), m.group(2)
        _ok, _why = claim_at(text_wo_code, m)      # **口径的唯一实现** ✓
        if not _ok:
            continue
        statement = re.sub(r'\s+', ' ', text_wo_code[max(0, m.start() - 30):m.end() + 30]).strip()
        hits.append({'number': n, 'unit': unit, 'statement': statement})
        if not re.search(r'(?<![\d.])' + n + r'\s*' + unit, pool):
            missing.append((n, unit))
    if missing:
        n, unit = missing[0]
        return {'pass': False,
                'reason': '共 %d 处数量陈述找不到出处（其一是「%s %s」；已声明来源：%s）'
                          % (len(missing), n, unit, '、'.join(srcs)),
                'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                'environment': {'kind': 'repo-fixture'},
                                'detail': {'number': n, 'unit': unit,
                                           'statement': hits[0]['statement'] if hits else '',
                                           'where': artifact['path'],
                                           'declared_sources': srcs,
                                           'missing_count': len(missing),
                                           'hits': hits[:10]}}}       # 前 10 处原文 ✓（证书不许大到没法读 ✓）
    return {'pass': True, 'reason': '', 'certificate': {'checked_units': sorted({u for _, u in QUANTITY.findall(text)})}}
