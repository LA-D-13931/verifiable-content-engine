#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内容规范域的共享定义（**唯一实现**）。

为什么单独一个模块：`_triple` 原本在本域三个检查文件里各写了一份——正是本项目
最忌的"同一段逻辑两处实现"。收敛到这里，顺带修掉一个真 bug：原来写的是
`'pass': bool(pass_)`，于是**「不适用」（None）被压成了 False**，三态失效。

三态的意义：静态检查在"运行时生成 DOM"的产物上会在**空集里通过**——那叫假绿。
所以判据要能明确返回"不适用"，而不是"通过"。
"""


def triple(pass_, reason='', certificate=None, advice=None):
    """{pass, reason, certificate} 三元组（判定契约）。

    `pass_` 允许三种取值：True 通过 / False 失败 / **None 不适用**。
    注意别写 `bool(pass_)`：那会把 None 变成 False。
    """
    out = {'pass': pass_ if pass_ is None else bool(pass_),
           'reason': reason, 'certificate': certificate}
    if advice:
        out['advice'] = advice
    return out
