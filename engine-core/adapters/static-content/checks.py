#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静态内容校验适配器 —— 领域二。

本文件把「静态站点的内容一致性校验」接进引擎，与交互任务判题（registry +
domains/<科目>）并列。两者共用同一套形状：

    一条声明式规则  →  一个可判定的检查  →  返回 { pass, reason, certificate }

区别只在**校验对象**：领域二校验的是 HTML 文档之间的关系（链接、锚点、标签配平），
而不是用户在参数空间里的操作。所以校验器与被校验对象之间同样必须是
「同一个事实的两个视角」——这里的事实是**文档集合与它们之间的引用**。

为什么要有这个适配器：主站此前有九套各自独立的校验脚本，输出格式各异、
失败时只报位置不给原因。它们的存在本身就证明「静态内容也需要自动校验」；
本适配器是把这件事收进引擎的第一次尝试（本次迁移 check-html.py 的四项检查）。
"""
from __future__ import annotations

import html.parser
import os
import re
from urllib.parse import unquote, urlsplit

#: 标签配平检查时忽略的标签：HTML 空元素与可省略闭合的标签
VOID_TAGS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
    'link', 'meta', 'param', 'source', 'track', 'wbr',
}
#: 这些标签允许不闭合（HTML 规范允许省略）
OPTIONAL_CLOSE = {'li', 'p', 'td', 'th', 'tr', 'dt', 'dd', 'option', 'thead', 'tbody'}


def _triple(pass_, reason='', certificate=None):
    return {'pass': bool(pass_), 'reason': reason, 'certificate': certificate}


class _TagBalance(html.parser.HTMLParser):
    """统计标签开合是否配平；记录每个问题的位置（行号）。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []          # [(tag, line)]
        self.problems = []
        self.counts = {}

    def _line(self):
        return self.getpos()[0]

    def handle_starttag(self, tag, attrs):
        if tag in VOID_TAGS:
            return
        self.counts[tag] = self.counts.get(tag, 0) + 1
        self.stack.append((tag, self._line()))

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        # 从栈顶往回找最近的同名开始标签
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                # 中间那些没闭合的标签：只有允许省略闭合的才放过
                for t, ln in self.stack[i + 1:]:
                    if t not in OPTIONAL_CLOSE:
                        self.problems.append(
                            '第 %d 行：<%s> 未闭合（在 </%s> 之前）' % (ln, t, tag))
                del self.stack[i:]
                return
        self.problems.append('第 %d 行：</%s> 没有对应的开始标签' % (self._line(), tag))

    def finish(self):
        for t, ln in self.stack:
            if t not in OPTIONAL_CLOSE:
                self.problems.append('第 %d 行：<%s> 未闭合' % (ln, t))
        return self.problems


def check_tag_balance(doc):
    """标签是否配平。"""
    p = _TagBalance()
    try:
        p.feed(doc['text'])
        p.close()
    except Exception as e:                       # 解析器自身出错也要报，不能静默
        return _triple(False, '解析失败：%s' % e, {'file': doc['rel']})
    problems = p.finish()
    if problems:
        return _triple(False, '；'.join(problems[:3]),
                       {'file': doc['rel'], 'problems': problems})
    return _triple(True, '', {'file': doc['rel'], 'tags': len(p.counts)})


LINK_RE = re.compile(r'(?:href|src)\s*=\s*"([^"]+)"', re.I)


def _strip_query(ref):
    return ref.split('#', 1)[0].split('?', 1)[0]


def check_internal_links(ctx):
    """站内链接是否都能落到真实文件上。

    只看站内（不以 http(s):// 或 // 开头、不是 mailto:/tel:/data:/javascript:）。
    """
    files = ctx['files']                 # rel 路径集合
    broken = []
    checked = 0
    for doc in ctx['docs']:
        base = os.path.dirname(doc['rel'])
        for ref in LINK_RE.findall(doc['text']):
            ref = ref.strip()
            if not ref or ref.startswith(('#', 'http://', 'https://', '//',
                                          'mailto:', 'tel:', 'data:', 'javascript:')):
                continue
            target = _strip_query(ref)
            if not target:
                continue
            checked += 1
            resolved = os.path.normpath(os.path.join(base, unquote(target)))
            if resolved in files or os.path.isdir(os.path.join(ctx['root'], resolved)):
                continue
            if ctx.get('allow_outside') and resolved.startswith('..'):
                if os.path.exists(os.path.join(ctx['root'], resolved)):
                    continue
            broken.append('%s → %s' % (doc['rel'], ref))
    return _triple(not broken,
                   '失效链接 %d 个：%s' % (len(broken), '；'.join(broken[:3])) if broken else '',
                   {'checked': checked, 'broken': broken})


ANCHOR_DEF_RE = re.compile(r'\bid\s*=\s*"([^"]+)"', re.I)


def check_in_page_anchors(ctx):
    """同一页内的 #锚点是否有对应的 id。"""
    ids_by_doc = {d['rel']: set(ANCHOR_DEF_RE.findall(d['text'])) for d in ctx['docs']}
    broken = []
    checked = 0
    for doc in ctx['docs']:
        for ref in LINK_RE.findall(doc['text']):
            if '#' not in ref:
                continue
            ref = ref.strip()
            if ref.startswith(('http://', 'https://', '//')):
                continue
            path, _, frag = ref.partition('#')
            if not frag:
                continue
            checked += 1
            if path:
                target = os.path.normpath(
                    os.path.join(os.path.dirname(doc['rel']), unquote(_strip_query(path))))
            else:
                target = doc['rel']
            if frag not in ids_by_doc.get(target, set()):
                broken.append('%s → %s' % (doc['rel'], ref))
    return _triple(not broken,
                   '失效锚点 %d 个：%s' % (len(broken), '；'.join(broken[:3])) if broken else '',
                   {'checked': checked, 'broken': broken})


#: 内容卫生的两条规则。它们都是「作者容易犯、但结构校验看不出来」的错：
#:   ① HTML 里写了 Markdown 的 **加粗** —— 浏览器会把星号原样显示出来
#:   ② SVG 里写了 $...$ 数学 —— **MathJax 不处理 SVG 内部文本**，
#:      那段字会被原样吞掉（主站 v0.7.0 的「定义域叠加图」就这么坏过一次）
#: 第 ② 条是迁移时从原脚本学到的：我原本自创了 TODO/undefined 那类规则，
#: 完全没想到 SVG 内数学这一条，而它才是真出过事故的那一类。
MARKDOWN_BOLD = re.compile(r'\*\*[^*\n]{1,60}\*\*')
SVG_BLOCK = re.compile(r'<svg.*?</svg>', re.S)
SVG_MATH = re.compile(r'\$[^$]{1,40}\$')


def check_content_hygiene(ctx):
    """内容卫生：正文里的 Markdown 星号、SVG 内的数学。"""
    hits = []
    for doc in ctx['docs']:
        src = doc['text']
        body = re.sub(r'<!--.*?-->', '', src, flags=re.S)   # 注释里的不算
        text = re.sub(r'<[^>]+>', ' ', body)                 # 去标签后看正文
        for m in MARKDOWN_BOLD.finditer(text):
            hits.append('%s 正文里有 Markdown 加粗：%s' % (doc['rel'], m.group(0)[:40]))
        for svg in SVG_BLOCK.finditer(body):
            for mm in SVG_MATH.finditer(svg.group(0)):
                hits.append('%s SVG 内出现数学 %s（MathJax 不处理 SVG 内部文本）'
                            % (doc['rel'], mm.group(0)[:30]))
    return _triple(not hits,
                   '%d 处：%s' % (len(hits), '；'.join(hits[:3])) if hits else '',
                   {'hits': hits})


#: 声明式检查表：name → (说明, 检查函数)
CHECKS = [
    ('tag-balance', '标签配平', lambda ctx: _all_docs(ctx, check_tag_balance)),
    ('internal-links', '站内链接可达', check_internal_links),
    ('in-page-anchors', '页内锚点存在', check_in_page_anchors),
    ('content-hygiene', '内容卫生', check_content_hygiene),
]


def _all_docs(ctx, per_doc_fn):
    """把逐文档的检查汇总成一条结果。"""
    problems = []
    for doc in ctx['docs']:
        r = per_doc_fn(doc)
        if not r['pass']:
            problems.append(r['reason'])
    return _triple(not problems,
                   '；'.join(problems[:3]) if problems else '',
                   {'files': len(ctx['docs']), 'problems': len(problems)})


#: 参与校验的页面（与主站 tests/check-html.py 同一套口径）。
#: 这是**显式列表**而不是「walk 整棵树」，原因：
#:   · tools/_backup/ 下有故意损坏的历史文件，不是站点内容
#:   · tests/ 下是测试代码本身
#: 教训：第一版适配器 walk 了整棵树，把 _backup 拉进来，于是标签配平与链接
#: 检查大量误报 —— 范围错了，而不是实现错了。
ROOT_PAGES = [
    'index.html', 'linear-algebra.html', 'exam.html', 'cheatsheet.html',
    'linear-algebra-exam.html', 'linear-algebra-cheatsheet.html',
]


def page_list(root):
    """站点页面清单：根页 + chapters/*.html（补充章是 suppN.html，故用 *.html）。"""
    pages = [p for p in ROOT_PAGES if os.path.isfile(os.path.join(root, p))]
    chdir = os.path.join(root, 'chapters')
    if os.path.isdir(chdir):
        pages += ['chapters/' + fn for fn in sorted(os.listdir(chdir))
                  if fn.lower().endswith('.html')]
    return pages


def collect(root):
    """收集待校验文档（页面清单）与全站文件集合（供链接可达性检查）。"""
    files, docs = set(), []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in {'.git', 'node_modules', '__pycache__'}]
        for fn in filenames:
            files.add(os.path.relpath(os.path.join(dirpath, fn), root))
    for rel in page_list(root):
        with open(os.path.join(root, rel), encoding='utf-8', errors='replace') as f:
            docs.append({'rel': rel, 'text': f.read()})
    return {'root': root, 'files': files, 'docs': docs}


def run(root, allow_outside=False):
    """跑全部检查，返回逐项结果。

    检查分两组：
      · 本文件里的声明式检查（CHECKS）—— 一条规则一个函数，已真正接进规则层
      · checks_structure.py 里的委托检查 —— 逻辑仍在原脚本，只接进报告层
    两组的差别是有意的，详见 checks_structure.py 的文件头。
    """
    ctx = collect(root)
    ctx['allow_outside'] = allow_outside
    out = []
    for name, label, fn in CHECKS:
        r = fn(ctx)
        out.append({'name': name, 'label': label, **r})
    for mod_name in ('checks_structure', 'checks_bilingual'):
        try:
            mod = __import__(mod_name)
        except ImportError:
            continue
        for name, label, fn in mod.CHECKS:
            r = fn(root)
            out.append({'name': name, 'label': label, 'delegated': True, **r})
    return {'root': root, 'docs': len(ctx['docs']), 'results': out}
