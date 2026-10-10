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


def _read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def _triple(pass_, reason='', certificate=None, advice=None):
    out = {'pass': bool(pass_), 'reason': reason, 'certificate': certificate}
    if advice:
        out['advice'] = advice
    return out


def undefined_style_token(artifact, source, base):
    """产物里 `var(--x)` 用到的每个变量，都必须在声明的样式来源里定义过 `--x:`。

    注意范围：扫的是产物**全文**（含 `<script>`）——因为坏例里那句
    `var(--lab-no)` 正是由内联脚本在运行时拼进 HTML 的，只看静态标记会漏掉。
    """
    apath = os.path.join(base, artifact['path'])
    if not os.path.isfile(apath):
        return _triple(False, '找不到产物 %s' % artifact['path'])
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
        return _triple(False, 'manifest 没有声明 style_sources，无法判定', cert)
    if undefined:
        return _triple(False,
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
    return _triple(True, '', cert)


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
    spath = os.path.join(base, artifact['path'])
    dpath = os.path.join(base, source.get('data', ''))
    if not os.path.isfile(spath) or not os.path.isfile(dpath):
        return _triple(False, '找不到渲染器源码或数据文件')
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
        return _triple(False, 'manifest 没有声明 enum_checks，无法判定')
    if bad:
        return _triple(False, '；'.join(bad), cert,
                       advice={'capabilities': [{
                           'capability': 'declared-value-vs-actual',
                           'title': '声明取值 vs 实际取值',
                           'generalize': '凡"有一处声明枚举、另一处实际使用"的地方都会漂移：'
                                         'CSS 档位、语言标记、题型名、难度名。'
                                         '两侧集合必须相等——多一个少一个都要报。',
                           'fix_hint': '决定以哪一侧为准：改声明（最常见）或改语料，然后两侧都重跑。',
                       }]})
    return _triple(True, '', cert)
