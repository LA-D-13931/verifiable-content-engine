#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""构建日志与逐步自检。

用途：把「每完成一步就自检、并留下可追溯记录」变成一条命令。

它做四件事：
  1. 跑全部自检项（矩阵层 / 关卡数据生成链 / 数据结构 / 交互回归 / 主题对比度）
  2. 记录当前 git 状态（提交号、工作区是否干净、相对上一个回滚标签的改动）
  3. 把结果追加到 00_工作区索引/构建日志.md
  4. 打印回滚方法

用法：
    python3 tools/build-log.py check                    只跑自检并记录
    python3 tools/build-log.py check --label W1-1b       带标签
    python3 tools/build-log.py check --commit "提交说明"  自检通过则提交并打回滚标签

设计原则：**自检不过就不允许提交**。日志里会如实记下失败项。
"""
import os
import re
import subprocess
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))


# --- 路径解析：统一走 tools/paths.py，不在各工具里数层数 ---
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import APP as SITE, ENGINE, REPO, WORKSPACE   # noqa: E402

LOG = os.path.join(WORKSPACE, '00_工作区索引', '构建日志.md')

# 自检项：(显示名, 命令, 通过标志)
CHECKS = [
    ('矩阵层：生成物最新 + 两侧同一个数学', ['python3', 'tools/verify-mat.py'], '全部通过'),
    ('判题注册表：离线回归（无需浏览器）', ['node', 'tools/verify-registry.mjs'], '全部通过'),
    ('引擎独立运行：全部任务可判定', ['node', 'tools/verify-engine.mjs'], '全部通过'),
    ('高等数学领域插件（第二科目）', ['node', 'tools/verify-calculus.mjs'], '全部通过'),
    ('诊断覆盖率：判不过必须给原因与证书', ['node', 'tools/verify-diagnostics.mjs'], '全部通过'),
    ('判题信息量审计（22 个类型两条路径）', ['node', 'tools/audit-coverage.mjs'], '所有类型'),
    ('领域插件与引擎 API 一致性', ['node', 'tools/verify-plugin-api.mjs'], '全部通过'),
    ('关卡数据：生成链无损', ['node', 'tools/verify-labs.mjs'], '全部通过'),
    ('数据结构与教学层', ['python3', 'tools/check-lab.py'], '全部通过'),
    ('动作序列矩阵复算', ['node', 'tools/verify-actions.js'], '全部通过'),
    ('真实交互与渲染', ['node', 'tools/smoke.js'], '全部通过'),
    ('8 组主题对比度', ['node', 'tools/verify-themes.js'], '全部通过'),
]


def run(cmd, cwd=SITE):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return r.returncode, (r.stdout or '') + (r.stderr or '')


def git(*args):
    rc, out = run(['git'] + list(args))
    return out.strip() if rc == 0 else ''


def outcome(rc, out):
    """判定一个检查项是否通过。

    不能只看「输出里有没有『全部通过』」——有些脚本失败时输出的是
    「失败 N 项 ✗」，也有的脚本即使有失败项仍会打印该关标题。
    稳妥的判据是：退出码为 0，且输出里没有「失败 N 项」。
    （第一版把通过项也标成了 ✗，还把失败项算进「通过」计数，两个 bug。）
    """
    m = re.search(r'失败\s*(\d+)\s*项', out)
    if m and int(m.group(1)) > 0:
        return False
    if re.search(r'全部通过', out):
        return rc == 0
    return rc == 0


def summarize(out):
    """从输出里挑一条最能说明结果的行。

    不能直接取末行：像 smoke.js 最后打印的是「无控制台错误 ✓」，
    看起来像通过，但前面可能已经列了失败项。
    优先找「失败 N 项」或「全部通过」这类结论行。
    """
    lines = [l.strip() for l in out.strip().split('\n') if l.strip()]
    for pat in (r'失败\s*\d+\s*项', r'全部通过'):
        for l in reversed(lines):
            if re.search(pat, l):
                return l
    return lines[-1] if lines else '(无输出)'


def run_checks():
    """跑全部自检，返回 [(名称, 是否通过, 说明)]。"""
    results = []
    print('=== 逐步自检 ===')
    for name, cmd, marker in CHECKS:
        rc, out = run(cmd)
        passed = outcome(rc, out)
        last = summarize(out)
        results.append((name, passed, last))
        print('  %s %-36s %s' % ('✓' if passed else '✗', name, last[:70]))
    return results


def append_log(label, results, commit, tag, dirty):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    head = git('rev-parse', '--short', 'HEAD')
    n_pass = sum(1 for _, p, _ in results if p)
    lines = []
    lines.append('')
    lines.append('## %s　%s' % (now, label or '(未命名步骤)'))
    lines.append('')
    lines.append('- 提交：`%s`%s' % (head, ('　回滚标签：`%s`' % tag) if tag else ''))
    lines.append('- 工作区：%s' % ('干净' if dirty == '' else '**有未提交改动**'))
    lines.append('- 自检：**%d / %d 通过**' % (n_pass, len(results)))
    lines.append('')
    lines.append('| 自检项 | 结果 | 说明 |')
    lines.append('|---|---|---|')
    for name, passed, last in results:
        lines.append('| %s | %s | %s |' % (name, '✅' if passed else '❌',
                                           last.replace('|', '／')[:80]))
    if commit:
        lines.append('')
        lines.append('- 提交说明：%s' % commit)
    lines.append('')
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    return n_pass


def main():
    if len(sys.argv) < 2 or sys.argv[1] != 'check':
        print(__doc__)
        return 2

    label = None
    commit_msg = None
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == '--label' and i + 1 < len(args):
            label = args[i + 1]
        if a == '--commit' and i + 1 < len(args):
            commit_msg = args[i + 1]

    results = run_checks()
    n_pass = sum(1 for _, p, _ in results)
    all_pass = n_pass == len(results)

    tag = None
    if commit_msg:
        if not all_pass:
            print('\n✗ 有自检项未通过，**拒绝提交**（日志已记录失败项）')
            append_log(label, results, commit_msg, None, git('status', '--short'))
            return 1
        run(['git', 'add', '-A'])
        rc, out = run(['git', 'commit', '-q', '-m', commit_msg])
        if rc != 0:
            print('提交失败：' + out)
            return 1
        safe = re.sub(r'[^A-Za-z0-9._-]+', '-', (label or 'step')).strip('-')
        tag = 'rb/%s-%s' % (safe, datetime.datetime.now().strftime('%m%d%H%M'))
        run(['git', 'tag', '-f', tag])
        print('\n✓ 已提交并打回滚标签：%s' % tag)

    dirty = git('status', '--short')
    append_log(label, results, commit_msg, tag, dirty)

    print('\n自检：%d / %d 通过' % (n_pass, len(results)))
    print('日志：%s' % os.path.relpath(LOG, WORKSPACE))
    if tag:
        print('回滚：git reset --hard %s' % tag)
        print('      git reset --hard %s^   （退到本步之前）' % tag)
    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
