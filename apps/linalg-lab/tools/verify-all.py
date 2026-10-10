#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键复现：把本引擎的全部自检跑一遍，给出汇总表。

为什么要有这个脚本：本项目的核心主张是「可复现」。但自检分散在 12 个脚本里，
评审者需要一份清单才知道该敲哪些命令。这个脚本把清单变成一条命令，
并且**用退出码表达结论**——可以直接接进 CI，也可以现场演示。

用法：
    python3 tools/verify-all.py                  # 离线部分（只要 Python 3 与 Node）
    python3 tools/verify-all.py --with-browser   # 另加需要 puppeteer-core 与 Edge/Chrome 的三项
    python3 tools/verify-all.py --with-adapter   # 另加需要主站快照的静态适配器差分对照
    python3 tools/verify-all.py --all            # 以上全部

退出码：
    0  全部通过
    1  有失败项
    2  环境不满足（缺 Node、缺依赖、缺快照）——**不算通过**，也不算代码失败
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import APP as SITE, ENGINE, REPO, WORKSPACE as _WS   # noqa: E402

PY = sys.executable

# (分组, 名称, 命令, 需要的能力)
CHECKS = [
    ('矩阵原语', 'Python 侧自检', [PY, os.path.join(ENGINE, 'mat.py')], None),
    ('矩阵原语', 'JS 侧与 Python 一致', ['node', 'tools/verify-mat.mjs'], None),
    ('矩阵原语', '两侧 + 生成物最新', [PY, 'tools/verify-mat.py'], None),
    ('矩阵原语', '独立裁决（精确有理数复算）', ['node', 'tools/audit-matrix-exact.mjs'], None),
    ('内容', '内容规范与缓存指纹', [PY, 'tools/check-lab.py'], None),
    ('内容', 'lab-data.js 可无损重建', ['node', 'tools/verify-labs.mjs'], None),
    ('引擎', '无浏览器跑完全部任务', ['node', 'tools/verify-engine.mjs'], None),
    ('引擎', '判题注册表回归', ['node', 'tools/verify-registry.mjs'], None),
    ('引擎', '第二科目复用同一接口', ['node', 'tools/verify-calculus.mjs'], None),
    ('引擎', '诊断覆盖率', ['node', 'tools/verify-diagnostics.mjs'], None),
    ('引擎', '诊断指向的失败条件正确', ['node', 'tools/verify-diagnosis-accuracy.mjs'], None),
    ('引擎', '插件 API 边界', ['node', 'tools/verify-plugin-api.mjs'], None),
    ('引擎', '逐类型信息量审计', ['node', 'tools/audit-coverage.mjs'], None),
    ('引擎', '判据区分力审计（抓恒真判据）', ['node', 'tools/audit-tautology.mjs'], None),
    ('浏览器', '冒烟（控制台无错误）', ['node', 'tools/smoke.mjs'], 'browser'),
    ('浏览器', '8 组主题对比度', ['node', 'tools/verify-themes.mjs'], 'browser'),
    ('浏览器', '真实拖拽与判题抽查', ['node', 'tools/verify-actions.mjs'], 'browser'),
    ('浏览器', '可视化页样例与内联引擎', ['node', 'tools/verify-visual.mjs'], 'browser'),
    ('静态适配器', '原脚本 vs 适配器差分', [PY, 'tools/verify-static-adapter.py'], 'adapter'),
    # 内容规范域（第三个域）。这一项**反证检查器本身**：真实坏例必须被抓、正常产物必须保持绿。
    # 所以真实坏例可以长期留作夹具 —— 它变绿反而说明检查器坏了。
    ('内容规范', '渲染能力（真实坏例必须被抓）',
     [PY, os.path.join(ENGINE, 'adapters', 'content-spec', 'runner.py'), '--selftest'], None),
]

PASS_MARKS = ('全部通过', '✓')

#: 环境不足（而非代码失败）的信号。刻意写窄：宽了会把真实失败误判成「环境问题」，
#: 那正是本项目最反对的失效模式（用「跳过」掩盖真问题）。
ENV_SIGNS = (
    'Cannot find module',          # node_modules 没装
    'ERR_MODULE_NOT_FOUND',
    '快照里没有',                   # 主站快照不在位
    '找不到讲义站 token',           # 兄弟站点不在位
    '目录不存在',
)


def last_meaningful_line(text):
    """取最后一行有意义的话——自检脚本的结论都写在最后。"""
    for line in reversed((text or '').strip().split('\n')):
        line = line.strip()
        if line and not line.startswith('['):
            return line
    return '(无输出)'


def main():
    argv = set(sys.argv[1:])
    want_browser = bool(argv & {'--with-browser', '--all'})
    want_adapter = bool(argv & {'--with-adapter', '--all'})

    print('=== 一键复现：可验证交互式教学内容引擎 ===')
    print('仓库：%s' % REPO)
    print('')

    rows = []
    for group, name, cmd, need in CHECKS:
        if need == 'browser' and not want_browser:
            rows.append((group, name, None, '跳过（需 --with-browser）'))
            continue
        if need == 'adapter' and not want_adapter:
            rows.append((group, name, None, '跳过（需 --with-adapter）'))
            continue
        if cmd[0] == 'node' and not _has('node'):
            rows.append((group, name, None, '跳过（未找到 node）'))
            continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=SITE, timeout=1800)
        except subprocess.TimeoutExpired:
            rows.append((group, name, None, '超时（>1800s）'))
            continue
        out = (r.stdout or '') + (r.stderr or '')
        if r.returncode == 0:
            rows.append((group, name, True, last_meaningful_line(r.stdout)))
        elif any(sign in out for sign in ENV_SIGNS) and r.returncode in (1, 2):
            rows.append((group, name, None, '环境不足：' + last_meaningful_line(out)))
        else:
            rows.append((group, name, False, last_meaningful_line(out)))

    width = max(len(n) for _, n, _, _ in rows) + 2
    cur = None
    for group, name, ok, detail in rows:
        if group != cur:
            print('── %s' % group)
            cur = group
        mark = {True: '✓', False: '✗', None: '–'}[ok]
        print('  %s %s%s' % (mark, name.ljust(width), detail))

    hard_fail = [n for _, n, ok, _ in rows if ok is False]
    skipped = [n for _, n, ok, _ in rows if ok is None]
    print('')
    if hard_fail:
        print('失败 %d 项 ✗' % len(hard_fail))
        for n in hard_fail:
            print('   - %s' % n)
        return 1
    print('全部通过 ✓  %d 项已跑、%d 项跳过' % (len(rows) - len(skipped), len(skipped)))
    if skipped:
        print('  （跳过不等于通过：加 --all 或装好依赖后再跑一遍）')
    return 0


def _has(prog):
    from shutil import which
    return which(prog) is not None


if __name__ == '__main__':
    sys.exit(main())
