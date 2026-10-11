#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""元检查（批次 C · 第八轮 D-1 的 5a 片）：**"打印跳过却 exit 0"** 必须判红，除非它是有意的。

判据（审计方给的，我照抄并写进判据里）：
> **"这个脚本退出 0 时，聚合层会不会把它记成通过？"** 会 → 必须改；不会 → 进白名单并注明理由。

机械识别：同一行（或其后 2 行内）既有「跳过/skipped」又有 `process.exit(0)`。
**白名单**（逐处判定过，附理由）：
  · `render-measure.mjs:33` 输出 `{"skipped": "找不到 Edge 或 Chrome（环境不足，不是通过）"}` 且 exit 0
  · `render-measure.mjs:37` 输出 `{"skipped": "puppeteer-core 不可用：…"}` 且 exit 0
    理由：`engine-core/adapters/content-spec/checks_render.py:56-57` 会读 `skipped` 键并转成
    `triple(None, '环境不足：…')` —— **聚合层把它记成"环境不足"，不是"通过"** → 不属于本检查要治的病。
    （反例：若哪天 `checks_render.py` 不再认 `skipped` 键，这两处就会变成"静默通过" → 本检查会失去豁免理由，
     所以白名单里同时记下"依赖 checks_render.py 认这个键"这一条前提。）

用法：python3 apps/linalg-lab/tools/check-skip-exit.py
退出码：0 = 无未豁免的命中；1 = 有
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
TOOLS = os.path.join(REPO, 'apps', 'linalg-lab', 'tools')
WHITELIST = {
    'render-measure.mjs:33': 'skipped 键被 checks_render.py:56 转成"环境不足" → 聚合层不会记成通过',
    'render-measure.mjs:37': '同上（puppeteer-core 不可用）',
}



def verify_premise():
    """第十七轮第 1 件：让豁免前提的校验**不依赖仓库外的可写性**。

    以前的做法（已废）：把假量测脚本 stage 到 `workspace_root()` 认的位置 ——
    而 `workspace_root()` **是引擎仓库的上两级** → 这个校验能否通过，
    取决于"调用者能不能写引擎仓库之外"：
      · 开发机：能写 → 退 0；
      · **审计方只读沙箱**：不能写 → 退 1（"校验不了 ≠ 通过"，行为本身对，但**它不该需要写**）；
      · **GitHub Actions**：取决于 runner 的 cwd 与布局 → **大概率红 = CI 首跑的拦路石**。

    现在：直接调 `checks_render.verdict_from_json()`（**纯函数**，只吃一个 dict）——
    不碰文件系统、不依赖 cwd、不依赖可写性、不产生任何中间文件 ✓。

    判据（三条，缺一不可）：
      ① `pass is None`（非通过态）；
      ② **reason 来自 skipped 分支**（含夹具文案）—— `pass is None` 是必要而非充分条件
         （`checks_render.py` 有 7 个 `return triple(None, …)` 早退分支，任一个都满足 ①）；
      ③ **校验不了也算红**（"验错了东西 ≠ 通过"）。
    """
    import importlib.util
    import sys as _sys
    _dir = os.path.join(REPO, 'engine-core', 'adapters', 'content-spec')
    if _dir not in _sys.path:
        _sys.path.insert(0, _dir)
    spec = importlib.util.spec_from_file_location('checks_render', os.path.join(_dir, 'checks_render.py'))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        return False, 'checks_render.py 无法加载：%s' % e
    fn = getattr(mod, 'verdict_from_json', None)
    if fn is None:
        return False, 'checks_render.py 里没有 verdict_from_json()（判定逻辑的位置变了，请人工确认）'
    payload = {'skipped': '批次 B 假量测输出'}
    try:
        t = fn(payload)
    except Exception as e:
        return False, '校验不了：verdict_from_json() 抛异常（%s）—— 校验不了 ≠ 通过' % e
    if isinstance(t, dict):
        got, reason = t.get('pass'), str(t.get('reason') or '')
    elif isinstance(t, tuple):
        got, reason = t[0], str(t[1] or '')
    else:
        got, reason = getattr(t, 'pass', None), str(getattr(t, 'reason', '') or '')
    hit = '批次 B 假量测输出' in reason
    if got is None and hit:
        return True, 'pass=None 且 reason 来自 skipped 分支（命中该分支）✓'
    if got is None:
        return False, ('pass=None，但**不是 skipped 分支**给的：%r '
                       '—— 这个校验没验到该验的东西（验错了东西 ≠ 通过）✗' % reason)
    return False, 'skipped 被转成了 pass=%r —— 豁免前提失效，白名单不再成立 ✗' % (got,)

def main():
    print('=== 元检查：打印跳过却 exit 0（批次 C）===')
    hits = []
    for name in sorted(os.listdir(TOOLS)):
        if not name.endswith('.mjs'):
            continue
        path = os.path.join(TOOLS, name)
        lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
        for i, line in enumerate(lines):
            window = '\n'.join(lines[i:i + 3])
            if re.search(r'跳过|skipped', line) and 'process.exit(0)' in window:
                key = '%s:%d' % (name, i + 1)
                hits.append((key, line.strip()[:110]))
    unwaived = [(k, t) for k, t in hits if k not in WHITELIST]
    premise_ok, why = verify_premise()
    print('  豁免前提校验：%s' % why)
    print('  命中 %d 处 ｜ 已豁免 %d 处（白名单带理由）｜ 未豁免 %d 处'
          % (len(hits), len(hits) - len(unwaived), len(unwaived)))
    for k, reason in WHITELIST.items():
        print('    ✓ 豁免 %s —— %s' % (k, reason))
    for k, text in hits:
        if k in WHITELIST:
            print('    · %s  %s' % (k, text))
    for k, text in unwaived:
        print('    ✗ %s  %s' % (k, text))
    if unwaived:
        print('\\n发现未豁免的"打印跳过却 exit 0" ✗（判据：聚合层会不会把它记成通过？）')
        return 1
    if not premise_ok:
        print('\n豁免前提**校验不了或已失效** ✗ —— 校验不了 ≠ 通过，那两处不能算数')
        return 1
    print('\\n没有未豁免的命中 ✓')
    return 0


if __name__ == '__main__':
    sys.exit(main())
