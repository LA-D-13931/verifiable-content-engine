#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""委托机制夹具：**总是通过**（退出码 0）。

它不检查任何真实内容——用途只有一个：证明"退出码 0 → 判定通过"这条链路是通的。
真实委托的例子见 manifest 里 gaoshu-site 的 delegate-numbering（站点自有的编号检查器）。
"""
print('夹具委托：检查了 3 项，全部通过')
raise SystemExit(0)
