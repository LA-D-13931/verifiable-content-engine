#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""源码级检查：**字段覆盖** 与 **自检覆盖面**。

这两条针对的是同一类病：**同一职责在多条渲染路径上分叉**。
产物级检查（checks_render_capability）能看出"某条路径缺能力"，但看不出
"这条路径是**哪几个字段**漏了"，也看不出"项目自己的自检只盯了其中一条路径"。
所以它们读**渲染器源码**——缺陷的源头。
"""
import os
import re

from common import triple


def _read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()




def _blocks(src):
    """按 `function name(` 切成块：(名字, 起始行号, 块文本)。"""
    marks = [(m.group(1), src.count('\n', 0, m.start()) + 1, m.start())
             for m in re.finditer(r'^\s*function (\w+)\(', src, re.M)]
    out = []
    for i, (name, line, off) in enumerate(marks):
        end = marks[i + 1][2] if i + 1 < len(marks) else len(src)
        out.append((name, line, src[off:end]))
    return out


def field_coverage(artifact, source, base):
    """每个**声明的文本字段**，在**每条渲染路径**里都必须经过转换函数。

    判据粒度是「字段 × 渲染函数」，而不是「文件」：真实坏例里片段渲染路径
    `q.text` / `o` / `e` 三个字段**各自**都裸拼进 HTML，而独立页三个都走了 `md()`。
    只看文件会漏掉"某条路径只漏了其中一个字段"这种情况。

    判据形状（不猜）：裸插值写作 `+ <字段> +`；走过转换的写作 `md(<字段>)`。
    声明在 manifest 的 `text_fields`。
    """
    path = os.path.join(base, artifact['path'])
    if not os.path.isfile(path):
        return triple(False, '找不到渲染器源码 %s' % artifact['path'])
    src = _read(path)
    fields = source.get('text_fields') or []
    if not fields:
        return triple(False, 'manifest 没有声明 text_fields，无法判定')

    cert, raw_hits = {}, []
    for fname, fline, body in _blocks(src):
        for field in fields:
            raws = [fname + ':' + str(fline + body.count('\n', 0, m.start()))
                    for m in re.finditer(r'\+\s*' + re.escape(field) + r'\s*\+', body)]
            wrapped = len(re.findall(r'\b\w+\(' + re.escape(field) + r'\)', body))
            if raws or wrapped:
                cert.setdefault(field, {})[fname] = {'raw': raws, 'wrapped': wrapped}
            raw_hits += ['%s 在 %s 里裸拼（%s）' % (field, a.split(':')[0], a) for a in raws]

    if not cert:
        return triple(False, '没扫到任何声明的文本字段（text_fields 与实际不符？）',
                       {'fields': fields})
    if raw_hits:
        return triple(False,
                       '%d 处字段没走转换：%s' % (len(raw_hits), '；'.join(raw_hits[:3])),
                       cert,
                       advice={'capabilities': [{
                           'capability': 'field-coverage',
                           'title': '字段覆盖（每个声明的文本字段都要走转换）',
                           'generalize': '同一份数据由多条渲染路径产出时，能力要按**字段**逐条比对，'
                                         '不能只按文件比对——按文件会漏掉"某条路径只漏一个字段"。',
                           'fix_hint': '把该字段的裸插值改成走转换函数（照同一文件里已经走转换的那条路径抄）。',
                       }]})
    return triple(True, '', cert)


def capability_matrix(artifact, source, base):
    """两条渲染路径的**能力矩阵**：未声明的分叉要报出来。

    真实坏例：独立页有 markdown 转换、讲评/报告、iframe 高度自适应，片段三个都没有——
    **没有任何地方声明这是有意差异**，于是它悄悄变成"片段能看不能讲评"。

    判据不发明需求：检查只做**差异登记**——某项能力只有部分渲染单元具备时，
    必须在 manifest 的 `allowed_divergence` 里逐条声明"有意如此"，否则算未声明分叉。
    （能力探针是**粗粒度**的：例如"HTML 转义"只要单元里出现过转义调用就算有，
      精确到字段的判定由 field-coverage 负责。）
    """
    path = os.path.join(base, artifact['path'])
    if not os.path.isfile(path):
        return triple(False, '找不到渲染器源码 %s' % artifact['path'])
    src = _read(path)
    # ⚠️ 要比的是**声明为可比**的单元：`STANDALONE_TEMPLATE` 是 HTML 模板、
    #    `*_JS` 是脚本，把它们放在一起比会假阳性（模板当然没有 JS 能力）。
    units = source.get('capability_units') or []
    caps = source.get('capabilities') or {}
    if not units or not caps:
        return triple(False, 'manifest 没有声明 capability_units 或 capabilities，无法判定')

    # 切出每个渲染单元的正文：从它的赋值行到下一个单元的赋值行
    marks = []
    for u in units:
        m = re.search(r'^%s\s*=' % re.escape(u), src, re.M)
        if m:
            marks.append((u, m.start()))
    marks.sort(key=lambda x: x[1])
    bodies = {}
    for i, (u, off) in enumerate(marks):
        end = marks[i + 1][1] if i + 1 < len(marks) else len(src)
        bodies[u] = src[off:end]
    if len(bodies) < 2:
        return triple(False, '只定位到 %d 个可比单元（capability_units 与实际不符？）' % len(bodies))

    matrix = {u: {c: bool(re.search(pat, b)) for c, pat in caps.items()} for u, b in bodies.items()}
    allowed = source.get('allowed_divergence') or []
    undeclared = []
    for cap in caps:
        present = [u for u in bodies if matrix[u][cap]]
        missing = [u for u in bodies if not matrix[u][cap]]
        if present and missing:
            for u in missing:
                if not any(d.get('capability') == cap and d.get('unit') == u for d in allowed):
                    undeclared.append({'capability': cap, 'missing_in': u, 'present_in': present})

    cert = {'units': list(bodies), 'matrix': matrix, 'allowed_divergence': allowed,
            'undeclared_divergence': undeclared}
    if undeclared:
        return triple(False,
                       '有 %d 处**未声明的能力分叉**：%s'
                       % (len(undeclared),
                          '；'.join('%s 在 %s 缺' % (d['capability'], d['missing_in'])
                                    for d in undeclared[:3])),
                       cert,
                       advice={'capabilities': [{
                           'capability': 'capability-matrix',
                           'title': '渲染能力矩阵',
                           'generalize': '同一职责的多条实现会各自长功能：今天缺讲评、明天缺导出。'
                                         '把"哪些差异是有意的"**声明出来**，剩下的差异就都是缺陷。',
                           'fix_hint': '二选一：把缺的能力补到该路径（照已实现的那条抄），'
                                       '或在 manifest 的 allowed_divergence 里逐条声明为有意差异并写明理由。',
                       }]})
    return triple(True, '', cert)


def selfcheck_path_coverage(artifact, source, base):
    """项目自己的自检，必须覆盖**全部**渲染路径。

    真实坏例：按钮名自检只把 `STANDALONE_TEMPLATE` / `STANDALONE_JS` 喂进去，
    片段那条路径的 `data-act` 与分支从未被检查过——于是两条路径的动作集已经分叉
    （片段有 `review`、独立页有 `correct`），而自检说"按钮与分支一致"。

    判据：模块级的渲染单元标识符（`*_TEMPLATE` / `*_JS` / `*_HTML`）
    必须都出现在自检的 `re.findall(..., <单元>)` 里。
    """
    path = os.path.join(base, artifact['path'])
    if not os.path.isfile(path):
        return triple(False, '找不到渲染器源码 %s' % artifact['path'])
    src = _read(path)
    fed = set(re.findall(r're\.findall\([^,]+,\s*([A-Z][A-Z0-9_]+)\s*\)', src))
    # ⚠️ 渲染单元由 manifest **声明**，不按名字猜：`REGISTRY_JS` / `NN_JUDGE_JS` 这类是
    #    被内联进来的**依赖**，不是渲染路径——按 `*_JS` 猜会把它们误当渲染路径上报。
    declared = source.get('render_units')
    units = set(declared) if declared else set(
        re.findall(r'^([A-Z][A-Z0-9_]*(?:_TEMPLATE|_JS|_HTML))\s*=', src, re.M))
    uncovered = sorted(units - fed)
    cert = {'render_units': sorted(units), 'fed_into_selfcheck': sorted(fed),
            'uncovered': uncovered}
    if not units:
        return triple(False, '没扫到任何渲染单元标识符（判据与实际不符？）', cert)
    if uncovered:
        return triple(False,
                       '自检只喂了 %d/%d 条渲染路径，未覆盖：%s'
                       % (len(fed & units), len(units), '、'.join(uncovered)),
                       cert,
                       advice={'capabilities': [{
                           'capability': 'selfcheck-path-coverage',
                           'title': '自检覆盖面',
                           'generalize': '项目自带的"自检"本身也会分叉：只盯一条渲染路径时，'
                                         '另一条路径的动作/分支分叉不会被任何检查发现。',
                           'fix_hint': '把未覆盖的单元也喂进同一条自检（或对每条路径各跑一遍）。',
                       }]})
    return triple(True, '', cert)
