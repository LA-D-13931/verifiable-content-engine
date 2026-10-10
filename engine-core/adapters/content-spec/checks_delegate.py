#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""委托机制：把**站点自有的检查脚本**按契约接进引擎。

## 为什么要有这个机制（不是"偷懒"，是分工）

Q13 定的原则：**通用且需要证书的判据自研；站点特有、且已有成熟实现的，委托。**
例子：站点自己写了 `tools/check-numbering.py`（中英编号一一对应，27 个脚本里的一员），
它对这个站的口径比我们熟；重要的是**结论要进入同一个判定契约**，
而不是各跑各的、结论散落在各个仓库里。

## 契约定成什么样

委托脚本必须：
  1. **退出码即结论**——0 通过、非 0 失败（站点脚本本来就是这么写的）；
  2. **只读**——必须显式声明 `read_only: true`，否则本检查**拒绝执行**
     （门禁里跑外部脚本有风险：一个会写文件的脚本足以让"检查"变成"破坏"）；
  3. **有超时**——必须声明 `timeout`（秒）。脚本卡住不能把整套门禁一起卡住。

## 三态

  · 脚本不在位（环境不足）→ **不适用**，并说明缺什么；
  · 退出码 0 → 通过（stdout 存进证书，可复核）；
  · 退出码非 0 → 失败（把脚本自己的输出当证据；修法指向**脚本自己的文档**，不是我们编的）；
  · 超时 → 失败，并写明"这不是内容问题，是环境或脚本卡住"。
"""
import os
import subprocess
import sys
import time

from common import resolve, triple

INTERPRETERS = {'.py': None, '.js': 'node', '.mjs': 'node', '.sh': 'bash'}


def run_delegate(artifact, source, base):
    script = resolve(artifact, base)
    cwd = None
    if artifact.get('cwd'):
        from common import workspace_root
        cwd = os.path.join(workspace_root(), artifact['cwd'])
    if not os.path.isfile(script):
        return triple(None, '环境不足：委托脚本不在位（%s）' % artifact['path'],
                      {'script': artifact['path'], 'present': False})

    # 守卫一：只读声明
    if not artifact.get('read_only'):
        return triple(False, '拒绝执行：委托未声明 read_only（门禁里跑会写文件的脚本 = 把检查变成破坏）',
                      {'script': artifact['path']}, advice={'capabilities': [{
                          'capability': 'delegate-guard',
                          'title': '委托只读守卫',
                          'generalize': '把一个"跑别人脚本"的能力交给门禁时，先问它会不会写。'
                                        '声明只读是入场券，不是可选礼貌。',
                          'fix_hint': '确认脚本只读后补 `read_only: true`；若脚本会写盘，不要委托它。',
                      }]})
    # 守卫二：超时
    timeout = artifact.get('timeout')
    if not timeout:
        return triple(False, '拒绝执行：委托未声明 timeout（卡住的脚本会拖死整套门禁）',
                      {'script': artifact['path']}, advice={'capabilities': [{
                          'capability': 'delegate-timeout',
                          'title': '委托超时',
                          'generalize': '外部脚本的失败方式不止"报错"——还有"永远不返回"。',
                          'fix_hint': '按实测耗时给一个宽松上限，例如 `timeout: 60`。',
                      }]})

    ext = os.path.splitext(script)[1]
    interp = INTERPRETERS.get(ext, ext.lstrip('.') or 'bash')
    cmd = ([sys.executable] if interp is None else [interp]) + [script] + list(artifact.get('args') or [])

    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return triple(False, '委托脚本超时（%.0f 秒）：这不是内容问题，是环境或脚本卡住' % timeout,
                      {'script': artifact['path'], 'timeout': timeout, 'cmd': cmd},
                      advice={'capabilities': [{
                          'capability': 'delegate-timeout',
                          'title': '委托超时',
                          'generalize': '外部脚本的失败方式不止"报错"——还有"永远不返回"。',
                          'fix_hint': '先手工跑一遍这个脚本看卡在哪；确认只是慢就调大 timeout。',
                      }]})
    except FileNotFoundError as e:
        return triple(None, '环境不足：解释器不可用（%s）' % e, {'cmd': cmd})
    secs = time.time() - t0

    out_tail = (p.stdout or '').strip().split('\n')[-14:]
    err_tail = (p.stderr or '').strip().split('\n')[-6:]
    cert = {'script': artifact['path'], 'cmd': ' '.join(cmd), 'cwd': cwd,
            'exit': p.returncode, 'seconds': round(secs, 2),
            'stdout_tail': out_tail, 'stderr_tail': err_tail}
    if p.returncode == 0:
        return triple(True, '', cert)
    # 工具故障 ≠ 内容缺陷：脚本自己没跑起来（解释器/依赖/语法问题）时，
    # 报「环境不足」而不是判红内容。判据看**合并输出**：
    # 实测 check-missing-math 的结论在 stdout、check-chart-visual 的崩溃**也在 stdout**
    # （"渲染失败：Node.js v24.17.0"）——只看 stderr 会漏。
    CRASH_SIGNS = ('Traceback (most recent call last)', 'Node.js v', 'Cannot find module',
                   'ModuleNotFoundError', 'command not found', 'SyntaxError')
    both = (p.stdout or '') + '\n' + (p.stderr or '')
    if any(sign in both for sign in CRASH_SIGNS):
        return triple(None, '环境不足：委托脚本自己没跑起来（不是内容问题）——%s'
                      % ((p.stderr or p.stdout or '').strip().split('\n')[-1][:120] or '见证书'),
                      cert)
    return triple(False, '委托脚本判定不通过（退出码 %d）：%s'
                  % (p.returncode, (out_tail or err_tail or ['（无输出）'])[-1][:120]),
                  cert,
                  advice={'capabilities': [{
                      'capability': 'delegate',
                      'title': '站点自有检查器判红',
                      'generalize': '站点自己的检查器对**本站在行的口径**比通用判据熟；'
                                    '委托它的结论，就不必在引擎里重写一套它的规矩。',
                      'fix_hint': '按该脚本的输出定位；口径与修法以**脚本自己的文档**为准'
                                  '（本项只负责把结论纳入同一契约）。',
                  }]})
