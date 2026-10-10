#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""纪律类检查：**声明的禁止模式** 与 **同作用域重复选择器**。

来源是两个真实项目的复盘台账（`失败模式台账.md` 第一、三节）：
用户 UI 规范的「明确禁止」12 条里，有多条是**静态可判**的——它们不该靠人记，该由检查守。

两条检查的分工：
  · `forbidden_patterns`：纯声明式。manifest 列出模式 + 理由 + 修法，产物命中即报。
    适合"整页平滑滚动""大区块 content-visibility:auto""折叠标题写成详见下文"这类
    **一眼可判、且没有例外**的禁止项。
  · `duplicate_selector`：同**作用域**内重复定义同一选择器。规范原话是
    「同类选择器只允许出现一次；改完用计数命令核对」，理由是"后面那条覆盖前面，布局被拆"。
    但重复**有时是有意的两步级联**——所以本检查不猜意图：**没声明的重复就报**，
    声明进 `allowed_duplicates` 的放过（与 `capability-matrix` 的 `allowed_divergence` 同一套做法）。

**两个假阳性教训（写进代码，不写进记忆）**：
  ① 色值正则曾命中 HTML 实体 `&#42;`（JS 里表示 Markdown 的 `*`）——那是"子串伪装"。
     所以色值只在 `<style>` 里查，且要排除前导 `&`；长度必须 ∈ {3,4,6,8}。
  ② 重复选择器必须**按 at-rule 作用域**分开统计：媒体查询/主题块里重复同一选择器是合法的。
"""
import collections
import os
import re

from common import resolve, triple

STYLE_BLOCK = re.compile(r'<style\b[^>]*>(.*?)</style>', re.S | re.I)
HEX_VALUE = re.compile(r'(?<!&)#([0-9a-fA-F]{1,8})(?![0-9a-fA-F])')
HEX_OK = (3, 4, 6, 8)          # CSS 允许的长度；4/8 带 alpha


def _read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def _file_of(artifact, base):
    p = resolve(artifact, base)
    return p if os.path.isfile(p) else None


def _scoped_selectors(html):
    """返回 [(作用域标签, 选择器, 出现次数)]，按 at-rule 分作用域统计。"""
    out = []
    for blk in STYLE_BLOCK.findall(html):
        blk = re.sub(r'/\*.*?\*/', ' ', blk, flags=re.S)
        parts, i = [], 1
        heads = re.split(r'(@[a-z-]+[^{]*\{)', blk)
        if len(heads) == 1:
            parts = [('顶层', blk)]
        else:
            parts = [('顶层', heads[0])]
            while i < len(heads):
                head = heads[i].strip()
                body, depth = '', 1
                for ch in (heads[i + 1] if i + 1 < len(heads) else ''):
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            break
                    body += ch
                parts.append((head[:48] or '顶层', body))
                i += 2
        for scope, body in parts:
            seen = collections.Counter()
            for m in re.finditer(r'(^|[};])\s*([^{}@][^{}]{0,120}?)\s*\{', body):
                for sel in m.group(2).split(','):
                    sel = ' '.join(sel.split())
                    if sel and not sel.startswith('@'):
                        seen[sel] += 1
            out += [(scope, s, c) for s, c in seen.items() if c > 1]
    return out


def forbidden_patterns(artifact, source, base):
    """manifest 声明的禁止模式，出现即报（每条带理由与修法）。"""
    path = _file_of(artifact, base)
    if not path:
        return triple(False, '找不到产物 %s' % artifact['path'])
    html = _read(path)
    rules = source.get('forbidden_patterns') or []
    if not rules:
        return triple(None, '本来源没有声明禁止模式（不适用）')
    hits, cert = [], {}
    for r in rules:
        found = []
        for m in re.finditer(r['pattern'], html, re.I | re.S):
            line = html.count('\n', 0, m.start()) + 1
            found.append({'line': line, 'snippet': ' '.join(m.group(0).split())[:70]})
        cert[r['id']] = {'why': r.get('why', ''), 'hits': len(found),
                         'at': [f['line'] for f in found[:4]]}
        if found:
            hits.append({'rule': r, 'found': found})
    if hits:
        head = hits[0]
        detail = '；'.join('%s（%s，共 %d 处，如第 %s 行）'
                          % (h['rule'].get('title', h['rule']['id']),
                             h['rule'].get('why', ''), len(h['found']),
                             h['found'][0]['line']) for h in hits[:3])
        return triple(False, '命中 %d 条禁止项：%s' % (len(hits), detail), cert,
                      advice={'capabilities': [{
                          'capability': 'forbidden-patterns',
                          'title': '禁止模式',
                          'generalize': '「禁止」类规则最容易被忘掉：写新代码时不会想起三年前的禁令。'
                                        '把它声明成模式，检查替你记着——命中就报，不靠人自觉。',
                          'locate': {'path': artifact['path'], 'lines': str(hits[0]['found'][0]['line']),
                                     'what': hits[0]['found'][0]['snippet']},
                          'fix_hint': hits[0]['rule'].get('fix', ''),
                      }]})
    return triple(True, '', cert)


def duplicate_selector(artifact, source, base):
    """同一作用域内重复定义同一选择器 —— 未声明的重复即报。

    产物**没有 `<style>` 块**时返回「不适用」（三态），不返回通过：
    没有样式表就无从谈起重复，而这种"空集上通过"正是我们要防的假绿。
    """
    path = _file_of(artifact, base)
    if not path:
        return triple(False, '找不到产物 %s' % artifact['path'])
    html = _read(path)
    if not STYLE_BLOCK.search(html):
        return triple(None, '产物没有 <style> 块（DOM 由运行时生成）—— 本项不适用',
                      {'style_blocks': 0})
    dups = _scoped_selectors(html)
    allowed = source.get('allowed_duplicates') or []
    unclaimed = [(s, sel, c) for s, sel, c in dups if sel not in allowed]
    bad_hex = []
    for blk in STYLE_BLOCK.findall(html):
        for m in HEX_VALUE.finditer(blk):
            if len(m.group(1)) not in HEX_OK:
                bad_hex.append(m.group(0))
    cert = {'duplicates': [{'scope': s, 'selector': sel, 'times': c} for s, sel, c in dups],
            'allowed_duplicates': allowed, 'unclaimed': [sel for _, sel, _ in unclaimed],
            'bad_hex_values': sorted(set(bad_hex))}
    if unclaimed:
        return triple(False,
                      '同一作用域内重复定义 %d 个选择器（未声明为有意）：%s'
                      % (len(unclaimed), '、'.join('%s×%d' % (sel, c) for _, sel, c in unclaimed[:4])),
                      cert,
                      advice={'capabilities': [{
                          'capability': 'duplicate-selector',
                          'title': '同作用域重复选择器',
                          'generalize': '同一选择器出现两次时，后一条静默覆盖前一条——'
                                        '改动其中一处会影响另一处的效果，而页面不会报错。'
                                        '若确实是有意的两步级联，就把它**声明**出来，别让下一个人重新踩。',
                          'locate': {'path': artifact['path'], 'lines': '', 'what': '见证据里的 duplicates'},
                          'fix_hint': '合并两处定义（推荐），或把该选择器加进 manifest 的 '
                                      'allowed_duplicates 并写明为什么是有意的。',
                      }]})
    if bad_hex:
        return triple(False, '出现非法色值：%s' % '、'.join(sorted(set(bad_hex))[:5]), cert,
                      advice={'capabilities': [{
                          'capability': 'legal-hex',
                          'title': '色值合法性（3/4/6/8 位）',
                          'generalize': '色值位数写错时整条声明失效，页面不报错只是颜色不对；'
                                        '批量替换短色值会踩这个坑（`#fff` 先匹配到 `#ffffff`）。',
                          'fix_hint': '把色值补成 3/4/6/8 位；批量替换时**长色值优先**。',
                      }]})
    return triple(True, '', cert)
