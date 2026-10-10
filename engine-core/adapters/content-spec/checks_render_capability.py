#!/usr/bin/env python3

from common import resolve, triple
# -*- coding: utf-8 -*-
"""渲染能力检查：产物是否具备「其数据所要求」的渲染能力。

**为什么是这条检查**：真实坏例里，同一份 JSON 由两条渲染路径产出——
独立小页有 Markdown 转换与样式块，注入片段两者都没有，于是反引号字面显示、
选项按浏览器默认 inline 挤成一行。根因不是内容，是**渲染器分叉**
（同一逻辑两份实现，本项目最忌的那条）。8 个课时**全部**如此。

**为什么不能静态扫"可见文本里的原始标记"**：实测坏例的可见文本里原始标记是 0 处
——反引号全在 `<script>` 内联数据里，页面是**运行时**用 JS 渲染的。
这恰好印证台账里的失败模式「静态校验通过就当没事」。所以判据不是"文本里有没有
反引号"，而是"**渲染路径有没有实现转换能力**"——这条能静态判定。

输出契约（与 static-content 一致的三元组 + 一个可选扩展）：
  · `{pass, reason, certificate}` —— 判定契约，证书是**可复核依据**（逐能力列出
    是否被数据要求 / 产物里是否具备 / 探测方式）
  · `advice`（可选，非判定契约的一部分）—— 面向**修复**的指引：定位、参照实现、
    修法提示、泛化方向。它的存在是为了让人/agent 拿到失败后能自己修好，
    而不是只收到一个 fail。
"""
import os

#: 能力表。required_if 由**数据**决定（不是拍脑袋），probe 是产物里的实现探测。
CAPABILITIES = [
    {
        'id': 'markdown-code',
        'title': '反引号 → <code> 转换',
        'required_if': lambda data: '`' in data,
        'require_note': '数据里含反引号代码片段（如 `(6,4) @ (4,5)`）',
        'probe': lambda html: '/`([^`]+)`/' in html,
        'probe_note': '产物里的替换实现：/`([^`]+)`/ → <code>',
        'why': '缺少它，反引号会字面显示成 `(6,4)`，而不是代码样式',
    },
    {
        'id': 'quiz-entry',
        'title': '判题入口（CheckRegistry / 判定）',
        'required_if': lambda data: '"options"' in data,
        'require_note': '这是自测产物（数据里有 options 题目）',
        'probe': lambda html: ('CheckRegistry' in html) or ('判定' in html),
        'probe_note': '产物里出现判题入口字样',
        'why': '缺少它，页面无法判定，自测不可用',
    },
]


def _read(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        return f.read()


def _advice_for(cap, source, product):
    """从 manifest 的 capability_refs 里取出「怎么修」的四件事。"""
    refs = (source.get('capability_refs') or {}).get(cap['id'], {})
    locate = ((refs.get('locate_by_role') or {}).get(product.get('role')) or None)
    return {
        'capability': cap['id'],
        'title': cap['title'],
        # ① 去哪看：缺陷所在的生成代码（比"产物是怎么被生成的"更精确）
        'locate': locate,
        # ② 照着谁改：同仓库里已经实现对的另一条路径
        'reference': refs.get('reference'),
        # ③ 怎么改
        'fix_hint': refs.get('fix_hint'),
        # ④ 还能往哪扩：这个判据的泛化方向
        'generalize': refs.get('generalize'),
    }


def run(product, source, base):
    """对**一个产物**做检查：数据要求的能力，它是否都具备。"""
    if 'data' not in source:
        # 缺声明 ≠ 内容有问题：报「不适用」，不崩、也不算通过（三态纪律）
        return {'pass': None, 'reason': '本来源未声明数据源（data），渲染能力检查不适用',
                'certificate': {'declared_data': None}}
    data_path = resolve({'path': source['data']}, base)
    prod_path = resolve(product, base)
    if not os.path.isfile(data_path):
        return {'pass': False, 'reason': '找不到数据源 %s' % source['data'], 'certificate': None}
    if not os.path.isfile(prod_path):
        return {'pass': False, 'reason': '找不到产物 %s' % product['path'], 'certificate': None}

    data, html = _read(data_path), _read(prod_path)
    cert, missing, advice = {}, [], []
    for cap in CAPABILITIES:
        required = bool(cap['required_if'](data))
        present = bool(cap['probe'](html)) if required else None
        cert[cap['id']] = {
            'required': required,
            'required_because': cap['require_note'] if required else '',
            'present': present,
            'probe': cap['probe_note'],
        }
        if required and not present:
            missing.append('%s（%s）' % (cap['title'], cap['why']))
            advice.append(_advice_for(cap, source, product))

    if missing:
        out = {'pass': False,
               'reason': '缺少 %d 项必需渲染能力：%s' % (len(missing), '；'.join(missing)),
               'certificate': cert}
        if advice:
            out['advice'] = {'capabilities': advice}
        return out
    return {'pass': True, 'reason': '', 'certificate': cert}
