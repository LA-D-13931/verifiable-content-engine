#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""委托机制夹具：**脚本自己跑挂**（不是内容有问题）。

用途：反证"工具故障 ≠ 内容缺陷"。它把异常打到 stderr，退出码非 0——
检查必须把它判成「环境不足」，而不是判红内容。
"""
import sys
sys.stderr.write('Traceback (most recent call last):\n  File "crash.py", line 1\nRuntimeError: 夹具故意崩溃\n')
raise SystemExit(3)
