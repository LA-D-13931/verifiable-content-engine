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
    """批次 B：**豁免前提必须被真实校验**（不能只写在注释里）。

    前提是：`checks_render.render_measure()` 会把量测脚本输出的 `{"skipped": …}` 转成**非 pass 态**。

    做法（**端到端**，不是读源码猜）：在 `tools/` 放一个**假量测脚本**（只打印
    `{"skipped": …}` 并 exit 0），再按真签名 `render_measure(artifact, source, base)` 调用它 ——
    这会走完"找脚本 → 找 node → 跑脚本 → 解析 JSON → 命中 skipped 分支"的**真实路径**，
    然后断言返回的 triple 里 `pass is None`。跑完删除假脚本。

    **改了就会红**：删掉 `checks_render.py` 的 `if 'skipped' in d:` 分支、或把它改成 `pass=True`
    → 返回不再是 `pass=None` → 本函数返回 False → 元检查退出码 1。
    **校验不了也算红**（"校验不了 ≠ 通过"）。
    """
    import importlib.util
    import sys as _sys
    import tempfile
    _dir = os.path.join(REPO, 'engine-core', 'adapters', 'content-spec')
    if _dir not in _sys.path:
        _sys.path.insert(0, _dir)
    spec = importlib.util.spec_from_file_location('checks_render', os.path.join(_dir, 'checks_render.py'))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        return False, 'checks_render.py 无法加载：%s' % e
    fn = getattr(mod, 'render_measure', None)
    if fn is None:
        return False, 'checks_render.py 里没有 render_measure()（转译位置变了）'

    fake = os.path.join(TOOLS, '_premise_fake_measure.mjs')
    tmpdir = tempfile.mkdtemp(prefix='premise-')
    page = os.path.join(tmpdir, 'x.html')
    open(page, 'w', encoding='utf-8').write('<!doctype html><title>premise</title>')
    open(fake, 'w', encoding='utf-8').write(
        'console.log(JSON.stringify({ skipped: "批次 B 假量测输出" }));\n')
    try:
        # script 相对 workspace_root()；tools/ 就在它下面
        source = {'render_measure': {'script': os.path.relpath(fake, os.path.dirname(TOOLS))},
                  'render_targets': ['premise']}
        artifact = {'id': 'premise', 'path': os.path.relpath(page, tmpdir)}
        t = fn(artifact, source, tmpdir)
        got = getattr(t, 'pass', None) if not isinstance(t, tuple) else t[0]
        if got is None:
            return True, '假量测输出 {"skipped": …} → render_measure() 返回 pass=None（非通过态）✓'
        return False, 'skipped 被转成了 pass=%r —— 豁免前提失效，白名单不再成立 ✗' % (got,)
    except Exception as e:
        return False, '校验不了：%s（校验不了 ≠ 通过）' % e
    finally:
        for f in (fake,):
            try:
                os.unlink(f)
            except OSError:
                pass
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

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
