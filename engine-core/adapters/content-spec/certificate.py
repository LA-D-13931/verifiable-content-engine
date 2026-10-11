#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证书契约（第三十轮 RX-05 第一步：C1 + C3 + C4 + C6）。

这个模块只做一件事：**让"证据"本身有形状**。它不落盘、不改输出格式
（落盘与人读可见是第二步 C2/C5 ✓）。

## C1 最小共同字段集
`CERT_FIELDS = ('verdict', 'evidence_type', 'environment', 'detail')`
—— 产证书时**缺任一字段** → 该条**判「检查器故障」**（不是内容失败、也不是环境不足）：
**没有形状的证据，比没有证据更危险**（它看起来像证据）。

## C3 四种"没给结论"必须分开
`environment`（要跑而跑不成）｜`no_judgment_surface`（这条检查没有可判的面）｜
`not_selected`（我没要求跑）｜`not_applicable`（跑了但不适用）。
**四者混成一类，就会把"没验"读成"验过"或"内容有问题"。**

## C4 环境必须**量到**，不许写字面量
（`checks_render.py` 里原来那个 `'browser': 'Edge/Chrome headless'` 就是字面量 ✗ —— 已删。）

## C6 `pass=False` 时证书**不许为 None**
判红必须有证据：哪条判据、看了什么、为什么判红。
"""
CERT_FIELDS = ('verdict', 'evidence_type', 'environment', 'detail')

#: C3：四种"没给结论"
NO_CONCLUSION_KINDS = ('environment', 'no_judgment_surface', 'not_selected', 'not_applicable')

#: reason 前缀 → 四种之一（**前缀是判据的一部分**，改前缀就要改这里）
_KIND_PREFIX = (
    ('环境不足', 'environment'),
    ('无判定面', 'no_judgment_surface'),
    ('未选择', 'not_selected'),
    ('不适用', 'not_applicable'),
)


def no_conclusion_kind(reason):
    """reason → 四种"没给结论"之一；**认不出就返回 None**（不猜 ✗）。"""
    for pref, kind in _KIND_PREFIX:
        if (reason or '').startswith(pref):
            return kind
    return None


def validate_certificate(cert):
    """C1：证书缺共同字段 → (False, 缺哪些)。**通过时返回 (True, [])**。"""
    if not isinstance(cert, dict):
        return False, ['（certificate 不是 dict：%r）' % type(cert).__name__]
    missing = [f for f in CERT_FIELDS if f not in cert]
    return (not missing), missing


def must_have_certificate(passed):
    """C6：`pass is False` 时证书不许为 None。"""
    return passed is False
