#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""站点级检查：**语言策略** 与 **单一数据源**。

这两条针对的是"整站范围"的不变量，所以输入不是单个产物，而是**一组页面**：

  · `lang_policy`：双语容器内中英段数必须相等；声明为纯中文的块里不得出现英文段；
    声明为"不要英文"的页面整页 0 个英文段。判据**按容器、按声明**，不按整页猜——
    真实站点里既有整段对照的双语容器，也有本就该纯中文的块（易错点/例题/讲评）。
  · `single_source`：声明为"必须逐字节相同"的块（导航、页脚）在全部页面里必须一致。
    根因写在站点自己的台账里：「反馈 1–12 条几乎全部源自同一个根因——导航被每个页面各写一份」。

路径与缺位：站点是**跨项目夹具**（不属于引擎仓库），由 manifest 的 `resolve: workspace`
声明；不在位时检查返回「环境不足」（None，三态），不假装通过。
"""
import glob as _glob
import hashlib
import os
import re

from common import resolve, triple


def _read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def _pages(artifact, source, base):
    """返回 (页面路径列表, 站点根, 错误说明)。"""
    root = resolve(artifact, base)
    if not os.path.isdir(root):
        return None, root, '环境不足：站点/快照不在位（%s）' % root
    if source.get('pages'):
        paths = [os.path.join(root, p) for p in source['pages']]
    else:
        paths = sorted(_glob.glob(os.path.join(root, source.get('pages_glob', '*.html'))))
    paths = [p for p in paths if os.path.isfile(p)]
    if not paths:
        return None, root, '环境不足：按 %r 没找到任何页面' % (source.get('pages') or source.get('pages_glob'))
    return paths, root, ''


def _divs(html, cls):
    """取出 class 含 cls 的 `<div>…</div>`（按 `<div>`/`</div>` 深度计数）。

    不引入外部 HTML 解析器（引擎本体零依赖）；对本站这种规整产物足够，
    深度计数也避免了"嵌套 div 被提前截断"这类假象。
    """
    out = []
    for m in re.finditer(r'<div[^>]*class="[^"]*\b%s\b[^"]*"[^>]*>' % re.escape(cls), html):
        i, depth = m.end(), 1
        while depth and i < len(html):
            nxt_open, nxt_close = html.find('<div', i), html.find('</div>', i)
            if nxt_close == -1:
                break
            if nxt_open != -1 and nxt_open < nxt_close:
                depth += 1
                i = nxt_open + 4
            else:
                depth -= 1
                i = nxt_close + 6
        out.append(html[m.start():i])
    return out


def lang_policy(artifact, source, base):
    pages, root, err = _pages(artifact, source, base)
    if err:
        return triple(None, err)
    bi_cls = source.get('bi_container_class', 'bi')
    zh_m = source.get('zh_marker', 'class="zh"')
    en_m = source.get('en_marker', 'class="en"')
    chinese_only = source.get('chinese_only_classes') or []
    no_en = set(source.get('no_english_pages') or [])

    problems, per_page = [], {}
    for p in pages:
        html = _read(p)
        rel = os.path.relpath(p, root)
        blocks = _divs(html, bi_cls)
        for i, blk in enumerate(blocks, 1):
            z, e = blk.count(zh_m), blk.count(en_m)
            if z != e:
                problems.append('%s 第 %d 个 .%s 容器中英段数不等：zh=%d en=%d' % (rel, i, bi_cls, z, e))
        for cls in chinese_only:
            for j, blk in enumerate(_divs(html, cls), 1):
                if en_m in blk:
                    problems.append('%s 第 %d 个 .%s（声明为纯中文）里出现英文段' % (rel, j, cls))
        if rel in no_en:
            n = html.count(en_m)
            if n:
                problems.append('%s 声明为"不要英文"，但整页有 %d 个英文段' % (rel, n))
        per_page[rel] = {'bi_blocks': len(blocks), 'en_marks': html.count(en_m)}

    cert = {'pages': len(pages), 'root': root, 'per_page': per_page, 'problems': problems[:8]}
    if problems:
        return triple(False, '%d 处语言策略不符：%s' % (len(problems), '；'.join(problems[:3])), cert,
                      advice={'capabilities': [{
                          'capability': 'lang-policy',
                          'title': '语言策略',
                          'generalize': '双语的"权重与范围"是**逐栏目**的策略，不是整站开关：'
                                        '有的块必须整段对照、有的块必须纯中文、有的页不要英文。'
                                        '把这些策略声明出来，检查才能逐条守——否则中英会慢慢漂。',
                          'fix_hint': '补齐/删掉成对的中英段，或把该块的策略写进 manifest 再重跑。',
                      }]})
    return triple(True, '', cert)


def single_source(artifact, source, base):
    pages, root, err = _pages(artifact, source, base)
    if err:
        return triple(None, err)
    specs = source.get('identical_blocks') or []
    if not specs:
        return triple(False, 'manifest 没有声明 identical_blocks，无法判定')

    cert, problems = {'pages': len(pages), 'blocks': {}}, []
    for spec in specs:
        rx = re.compile(spec['regex'], re.S)
        digests, missing = {}, []
        for p in pages:
            rel = os.path.relpath(p, root)
            m = rx.search(_read(p))
            if not m:
                missing.append(rel)
                digests[rel] = None
            else:
                digests[rel] = hashlib.sha256(m.group(0).encode('utf-8')).hexdigest()[:12]
        uniq = sorted({v for v in digests.values() if v})
        cert['blocks'][spec['name']] = {'digests': digests, 'distinct': len(uniq)}
        if missing:
            problems.append('%s 在 %d 个页面里缺失（%s）' % (spec['name'], len(missing), '、'.join(missing[:3])))
        if len(uniq) > 1:
            odd = [k for k, v in digests.items() if v and v != uniq[0]]
            problems.append('%s 在各页**不一致**：%d 个版本，异常页如 %s'
                            % (spec['name'], len(uniq), '、'.join(odd[:3])))
    if problems:
        return triple(False, '%d 处单一数据源被破坏：%s' % (len(problems), '；'.join(problems[:3])), cert,
                      advice={'capabilities': [{
                          'capability': 'single-source',
                          'title': '单一数据源',
                          'generalize': '凡是"每个页面各写一份"的东西都会漂：导航、页脚、状态标记、'
                                        '章节清单。把它改成**一处生成**，再守住"各页逐字节相同"这条不变量。',
                          'fix_hint': '找到那个被单独改动的页面，让它重新由同一数据源生成；'
                                      '（本站的根因就是导航曾被每页各写一份，后改为单一数据源生成）。',
                      }]})
    return triple(True, '', cert)
