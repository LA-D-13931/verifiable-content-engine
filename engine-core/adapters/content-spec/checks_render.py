#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染量测检查：**本域第一条 `render` 证据的检查**。

治的是台账 M2 的另一半——「静态校验全过，页面真的坏着」：
句末黑块、对比度一路漏到用户截图、图的硬伤，都属于"静态看不见"的那一类。

做法：把页面放进**真实浏览器**（量测脚本在消费者侧 `apps/linalg-lab/tools/render-measure.mjs`，
按本项目既有分工：规则层在本域、量测层在消费者侧），量三件事——
  ① 横向溢出（用户 UI 规范「改完必做的自检」第 1 条：无异常横向滚动条）
  ② 过小的独立控件（正文内联链接**不算**：那是经典假阳性）
  ③ 页面脚本报错（交互组件坏了往往先在这里露头）

三态：浏览器不在 / 脚本不在 / 量测超时 → **不适用**（环境不足），不假装通过。
只在 `render_targets` 里声明的产物上跑——浏览器启动有成本，跑哪些必须是**明写的选择**，
不能靠"顺手全跑一遍"。
"""
import json
import os
import subprocess
import sys
from shutil import which

from common import resolve, triple, workspace_root


def verdict_from_json(d):
    """**纯函数**（第十七轮第 1 件）：量测脚本 JSON 输出 → 判定三元组。

    为什么抽出来：元检查（tools/check-skip-exit.py）要验证
    「`{"skipped": …}` 会被转成非 pass 态」这条豁免前提。
    原先它只能**端到端**跑（stage 一个假脚本到 `workspace_root()` 之外）——
    那使这个检查**依赖"调用者能写引擎仓库之外"**：审计方的只读沙箱里必红，
    GitHub Actions 上则取决于 runner 的 cwd 与布局 → **CI 真实首跑会撞上它**。

    抽成纯函数之后：**不碰文件系统、不依赖 cwd、不依赖可写性**，CI 上也稳。
    代价：元检查不再是"端到端"——但那个"端到端"本来就必须写在仓库外，得不偿失。

    ⚠️ 这条分支的形状（`if 'skipped' in d:`）**是判据的一部分**：
    反例脚本按它做变异（改成 `if False and …`）来验证元检查真的在验东西。
    """
    if 'skipped' in d:
        return triple(None, '环境不足：%s' % d['skipped'])


def _render_measure_one(artifact, source, base):
    """单档量测（第二十一轮前的原实现，内部一字未改）。"""
    spec = source.get('render_measure')
    if not spec:
        return triple(None, '本来源没有声明渲染量测（不适用）')
    targets = source.get('render_targets') or []
    if artifact['id'] not in targets:
        return triple(None, '未列入 render_targets（浏览器启动有成本：跑哪些必须明写）',
                      {'render_targets': targets})

    script = os.path.join(workspace_root(), spec['script'])
    page = resolve(artifact, base)
    if not os.path.isfile(script):
        return triple(None, '环境不足：量测脚本不在位（%s）' % spec['script'])
    if which('node') is None:
        return triple(None, '环境不足：找不到 node')
    if not os.path.isfile(page):
        return triple(None, '不适用：产物不在位由 runner 的统一门负责（第五十五轮 ✓）')

    cmd = ['node', script, page, '--width', str(spec.get('width', 1440)),
           '--min-tap', str(spec.get('min_tap_px', 20))]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=spec.get('timeout', 180))
    except subprocess.TimeoutExpired:
        return triple(None, '环境不足：量测超时（%.0f 秒）' % spec.get('timeout', 180))
    raw = (p.stdout or '').strip().split('\n')[-1] if p.stdout else ''
    try:
        d = json.loads(raw)
    except Exception:
        return triple(None, '环境不足：量测脚本没有返回 JSON（%s）' % (raw[:120] or (p.stderr or '')[-120:]))
    if 'skipped' in d:
        return verdict_from_json(d)      # 判定逻辑只有一份（台账 M1）
    if 'error' in d:
        return triple(False, '页面加载或量测失败：%s' % d['error'][:160], {'raw': d})

    max_ov = spec.get('max_overflow_px', 1)
    problems = []
    if d.get('overflowX', 0) > max_ov:
        problems.append('横向溢出 %spx（阈值 %s）' % (d['overflowX'], max_ov))
    if d.get('smallTapCount', 0) > 0:
        t = (d.get('smallTaps') or [{}])[0]
        problems.append('%d 个独立控件小于 %spx（如 %s %s×%s「%s」）'
                        % (d['smallTapCount'], spec.get('min_tap_px', 20),
                           t.get('tag'), t.get('w'), t.get('h'), t.get('text', '')))
    if d.get('pageErrors'):
        problems.append('%d 条页面脚本报错（如 %s）' % (len(d['pageErrors']), d['pageErrors'][0][:80]))
    cert = {'evidence': 'render', 'browser': d.get('browser') or '（量测脚本未回报浏览器）', 'width': d.get('width'),
            'overflowX': d.get('overflowX'), 'nodes': d.get('nodes'),
            'scrollHeight': d.get('scrollHeight'), 'smallTapCount': d.get('smallTapCount'),
            'smallTaps': d.get('smallTaps'), 'pageErrors': d.get('pageErrors')}
    if problems:
        return triple(False, '浏览器里量到 %d 处问题：%s' % (len(problems), '；'.join(problems[:3])), cert,
                      advice={'capabilities': [{
                          'capability': 'render-measure',
                          'title': '渲染量测（真实浏览器）',
                          'generalize': '有些缺陷静态永远看不见：溢出、太小点不到、脚本报错。'
                                        '它们只在**渲染出来**之后存在——所以要有一个真的把页面打开的检查。',
                          'fix_hint': '用 `node apps/linalg-lab/tools/render-measure.mjs <页面>` '
                                      '单跑这一页，按输出的三个数定位；同样是"重新测量过才算修好"。',
                      }]})
    return triple(True, '', cert)

def render_measure(artifact, source, base):
    """渲染量测（第二十一轮：**宽度可声明为多档**）。

    - `render_measure.width` 是**标量**（如 `1440`）→ 完全保持原行为（现有 manifest 不必改）；
    - 是**数组**（如 `[1440, 320]`）→ **同一产物逐档跑**，**每档各出一条判定、各自带自己的宽度**。

    阈值（`min_tap_px` / `max_overflow_px`）**不随宽度变** —— 判断与理由写在回复里：
    "点击目标 ≥20px"是一条**与视口无关的可达性下限**，窄屏不该放宽它（放宽就是把阈值调松换绿）。

    组合规则：任一档**环境不足** → 整条记环境不足（并点名是哪一档）；任一档**判据不成立** → 记失败（点名哪一档）。
    """
    spec = source.get('render_measure') or {}
    widths = spec.get('width', 1440)
    if not isinstance(widths, (list, tuple)):
        return _render_measure_one(artifact, source, base)

    results = []
    for w in widths:
        src2 = dict(source)
        src2['render_measure'] = dict(spec, width=w)      # 该档用标量宽度调原实现
        results.append((w, _render_measure_one(artifact, src2, base)))

    per = []
    for w, t in results:
        d = t if isinstance(t, dict) else {'pass': t[0], 'reason': t[1]}
        per.append({'width': w, 'pass': d.get('pass'), 'reason': d.get('reason')})

    env = [(w, t) for w, t in results if (t if isinstance(t, dict) else {'pass': t[0]}).get('pass') is None]
    bad = [(w, t) for w, t in results if (t if isinstance(t, dict) else {'pass': t[0]}).get('pass') is False]

    if env:
        w, t = env[0]
        return triple(None, '环境不足（宽度 %s）：%s' % (w, (t if isinstance(t, dict) else {'reason': t[1]}).get('reason')),
                      {'evidence': 'render', 'widths': list(widths), 'per_width': per})
    if bad:
        w, t = bad[0]
        return triple(False, '浏览器里量到问题（宽度 %s）：%s'
                      % (w, (t if isinstance(t, dict) else {'reason': t[1]}).get('reason')),
                      {'evidence': 'render', 'widths': list(widths), 'per_width': per})
    return triple(True, '', {'evidence': 'render',
                             'width': per[0]['width'],            # 兼容：仍给一个 width
                             'widths': list(widths), 'per_width': per})
