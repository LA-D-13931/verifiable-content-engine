#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""样式级检查：**声明取值 vs 实际取值** 与 **用了但未定义的样式变量**。

两条都属于「声明与使用不一致」这一类——不报错、也不崩，只是**静默地不生效**：
难度档声明了 `.df.考研` 而语料里叫「综合」，于是第三档没有配色；
`var(--lab-no)` 全项目没有定义、又没有回退值，于是判定失败时的 ✗ 不上色。
这类缺陷连"渲染出来看一眼"都不容易发现，正好适合做成检查。
"""
import json
import os
import re

from common import resolve, triple


def _read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()




STYLE_BLOCK = re.compile(r'<style\b.*?</style>', re.S | re.I)
CLASS_IN_TAG = re.compile(r'<[a-zA-Z][\w-]*[^>]*\bclass="([^"]*)"')
CSS_RULE = re.compile(r'\.([A-Za-z_][\w-]*)')


def style_coverage(artifact, source, base):
    """静态标记里用到的每个类名，都要能在声明的样式来源里找到规则。

    **三态**：如果产物的静态标记里**一个类名都没有**（DOM 完全由运行时 JS 生成），
    这条检查返回「不适用」而不是「通过」——那种情况下静态扫类名是在**空集上通过**，
    也就是假绿。真实坏例正是如此：片段 HTML 去掉 `<script>` 后不含任何类名与文本。
    """
    apath = resolve(artifact, base)
    if not os.path.isfile(apath):
        return triple(False, '找不到产物 %s' % artifact['path'])
    html = _read(apath)
    markup = re.sub(r'<script\b.*?</script>', ' ', html, flags=re.S | re.I)
    used = set()
    for m in CLASS_IN_TAG.finditer(markup):
        used |= {c for c in m.group(1).split() if c}
    cert = {'classes_used_in_static_markup': sorted(used)}
    if not used:
        cert['why'] = ('静态标记里没有类名（DOM 由运行时生成）——静态类名检查在这里无效，'
                       '要验只能走渲染层')
        return triple(None, '不适用：静态标记里没有类名，静态检查会在空集上通过（假绿）', cert)

    rules = set()
    for blk in STYLE_BLOCK.findall(html):
        rules |= set(CSS_RULE.findall(blk))
    for rel in (source.get('style_sources') or []):
        p = os.path.join(base, rel)
        if os.path.isfile(p):
            rules |= set(CSS_RULE.findall(_read(p)))
    undefined = sorted(used - rules)
    cert.update({'rules_found': len(rules), 'undefined': undefined})
    if undefined:
        return triple(False,
                       '%d 个类名没有任何样式规则：%s（浏览器按默认样式排 → 常见表现是挤成一行）'
                       % (len(undefined), '、'.join(undefined[:6])), cert,
                       advice={'capabilities': [{
                           'capability': 'style-coverage',
                           'title': '类名覆盖',
                           'generalize': '「产出的类名」与「写好的样式」分居两处时，改前缀、改模板'
                                         '都会让某一侧静默失配——页面不报错，只是排得不对。',
                           'fix_hint': '给这些类名补样式规则，或把模板里的类名改成已有规则的名字；'
                                       '注意前缀约定（本项目片段用 lab- 前缀正是为了不污染站点样式）。',
                       }]})
    return triple(True, '', cert)


def undefined_style_token(artifact, source, base):
    """产物里 `var(--x)` 用到的每个变量，都必须在声明的样式来源里定义过 `--x:`。

    注意范围：扫的是产物**全文**（含 `<script>`）——因为坏例里那句
    `var(--lab-no)` 正是由内联脚本在运行时拼进 HTML 的，只看静态标记会漏掉。
    """
    apath = resolve(artifact, base)
    if not os.path.isfile(apath):
        return triple(False, '找不到产物 %s' % artifact['path'])
    html = _read(apath)
    used = set(re.findall(r'var\(\s*(--[\w-]+)', html))
    style_sources = source.get('style_sources') or []
    defined = set()
    for rel in style_sources:
        p = os.path.join(base, rel)
        if os.path.isfile(p):
            defined |= set(re.findall(r'(--[\w-]+)\s*:', _read(p)))
    undefined = sorted(used - defined)
    cert = {'used': sorted(used), 'defined_in_sources': sorted(defined),
            'style_sources': style_sources, 'undefined': undefined}
    if not style_sources:
        return triple(False, 'manifest 没有声明 style_sources，无法判定', cert)
    if undefined:
        return triple(False,
                       '有 %d 个样式变量用了但没有任何定义：%s（var() 无回退值 → 静默不生效）'
                       % (len(undefined), '、'.join(undefined)),
                       cert,
                       advice={'capabilities': [{
                           'capability': 'undefined-style-token',
                           'title': '未定义的样式变量',
                           'generalize': '「声明处」和「使用处」分居两处时会出现静默失效：'
                                         '用了没定义、定义了没用、名字差一个字——都不报错。',
                           'fix_hint': '在样式来源里补上该变量的定义，或改用法去掉它；'
                                       '顺手确认 `defined` 里有没有反向的"定义了但没人用"。',
                       }]})
    return triple(True, '', cert)


def _collect_values(obj, key, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, str):
                out.add(v)
            _collect_values(v, key, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_values(v, key, out)


def declared_value_vs_actual(artifact, source, base):
    """声明处枚举的取值集合，必须等于语料里**实际出现**的取值集合。

    真实坏例：渲染器声明 `.df.基础/.df.中等/.df.考研`，而教材语料实际用的是
    「基础/中等/**综合**」——两边各有一个对方没有的值，于是第三档没有配色，
    而声明里那个"考研"从来没被用过。项目自己的决策记录里也记过这条不一致。

    判据：`declared_regex` 从渲染器源码里取声明值；`actual_key` 从数据文件里取实际值。
    """
    spath = resolve(artifact, base)
    dpath = os.path.join(base, source.get('data', ''))
    if not os.path.isfile(spath) or not os.path.isfile(dpath):
        return triple(False, '找不到渲染器源码或数据文件')
    src, data = _read(spath), json.load(open(dpath, encoding='utf-8'))
    cert, bad = {}, []
    for ec in (source.get('enum_checks') or []):
        declared = set(re.findall(ec['declared_regex'], src))
        actual = set()
        _collect_values(data, ec['actual_key'], actual)
        only_declared = sorted(declared - actual)
        only_actual = sorted(actual - declared)
        cert[ec['name']] = {'declared': sorted(declared), 'actual': sorted(actual),
                            'declared_but_unused': only_declared,
                            'used_but_undeclared': only_actual}
        if only_declared or only_actual:
            bad.append('%s：声明了没用到的 %s；用了没声明的 %s'
                       % (ec['name'], only_declared or '无', only_actual or '无'))
    if not cert:
        return triple(False, 'manifest 没有声明 enum_checks，无法判定')
    if bad:
        return triple(False, '；'.join(bad), cert,
                       advice={'capabilities': [{
                           'capability': 'declared-value-vs-actual',
                           'title': '声明取值 vs 实际取值',
                           'generalize': '凡"有一处声明枚举、另一处实际使用"的地方都会漂移：'
                                         'CSS 档位、语言标记、题型名、难度名。'
                                         '两侧集合必须相等——多一个少一个都要报。',
                           'fix_hint': '决定以哪一侧为准：改声明（最常见）或改语料，然后两侧都重跑。',
                       }]})
    return triple(True, '', cert)
