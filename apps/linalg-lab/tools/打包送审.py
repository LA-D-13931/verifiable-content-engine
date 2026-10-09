#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打一个「送审包」——交给别的 agent 或人审代码用。

与 tools/打包交付.py 的区别（两个包的用途不同，别混）
=====================================================
  打包交付.py   给**开发者用**：轻量、面向集成，砍掉一切与「怎么用引擎」无关的东西
  本脚本        给**审查者看**：完整、可复现，要能看懂设计意图，也要能挑刺

所以本包多出：
  · 一份《给审查者的说明.md》放在最外层 —— 否则审查者不知道该审什么
  · 校验工具全套（含自检的「自检」）
  · 已知局限的清单（第八条刻意列了 8 项，包括我们自己没解决的问题）
  · 保留仓库原结构（工具里的相对路径依赖它；压平会让工具全断）

用法：python3 tools/打包送审.py [--out 目录]
"""
import argparse
import os
import shutil
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(APP))

PKG_NAME = '送审_教学内容引擎'
VERSION = 'v1'

#: 不进包：依赖、缓存、二进制噪声、与审查无关的产物
EXCLUDE_DIRS = {'node_modules', '__pycache__', 'shots', '_backup', '.git',
                '.github', '审查包'}
EXCLUDE_FILES = {'package-lock.json', '.DS_Store'}
EXCLUDE_EXT = {'.pyc', '.log'}

#: 审查者最该看到的文件 —— 少一个就说明打包漏了
REQUIRED = [
    '给审查者的说明.md',
    'engine-core/README.md',
    'engine-core/registry.js',
    'engine-core/mat.py',
    'engine-core/mat.js',
    'engine-core/domains/linalg/judge.js',
    'engine-core/domains/calculus/judge.js',
    'engine-core/adapters/static-content/verify.py',
    'apps/linalg-lab/tools/verify-engine.mjs',
    'apps/linalg-lab/tools/verify-diagnosis-accuracy.mjs',
    'apps/linalg-lab/tools/verify-plugin-api.mjs',
    'apps/linalg-lab/assets/js/labs.json',
    'apps/linalg-lab/引擎可视化_单文件版.html',
]


def sh_rm(p):
    if os.path.exists(p):
        shutil.rmtree(p)


def stage(dest):
    """按仓库原结构复制 —— 工具的相对路径依赖它，不能压平。"""
    sh_rm(dest)
    os.makedirs(dest)
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        rel = os.path.relpath(root, REPO)
        rel = '' if rel == '.' else rel
        os.makedirs(os.path.join(dest, rel), exist_ok=True)
        for f in files:
            if f in EXCLUDE_FILES or os.path.splitext(f)[1] in EXCLUDE_EXT:
                continue
            shutil.copy2(os.path.join(root, f), os.path.join(dest, rel, f))
    # 审查指南放到最外层
    guide = os.path.join(HERE, '审查包', '给审查者的说明.md')
    assert os.path.isfile(guide), '找不到审查指南：%s' % guide
    shutil.copy2(guide, os.path.join(dest, '给审查者的说明.md'))
    return dest


def audit(dest):
    problems = []
    for r in REQUIRED:
        if not os.path.isfile(os.path.join(dest, r)):
            problems.append('缺少必需文件：%s' % r)
    # 不该出现的东西
    for root, dirs, files in os.walk(dest):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), dest)
            low = rel.lower()
            if any(low.endswith(e) for e in ('.pdf', '.dmg', '.exe', '.pem', '.key')):
                problems.append('不该入库的文件：%s' % rel)
            if '.keys/' in low or 'node_modules' in low:
                problems.append('不该入库的路径：%s' % rel)
    return problems


def make_zip(src, out_zip):
    """用 Python 打 zip：它会为非 ASCII 名设置 UTF-8 标志位（0x800）。
    用 macOS 的 zip 命令不行 —— 不设标志，Windows 解压会乱码。"""
    if os.path.exists(out_zip):
        os.remove(out_zip)
    n = 0
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in sorted(files):
                full = os.path.join(root, f)
                z.write(full, os.path.join(PKG_NAME, os.path.relpath(full, src)))
                n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.expanduser('~/Desktop'))
    args = ap.parse_args()

    work = tempfile.mkdtemp(prefix='review-pkg-')
    try:
        print('=== 打送审包 ===')
        src = stage(os.path.join(work, PKG_NAME))
        n = sum(len(fs) for _, _, fs in os.walk(src))
        size = sum(os.path.getsize(os.path.join(r, f))
                   for r, _, fs in os.walk(src) for f in fs)
        print('  暂存 %d 个文件 / %.1f MB' % (n, size / 1024 / 1024))

        print()
        print('=== 体检 ===')
        problems = audit(src)
        if problems:
            for p in problems:
                print('  ✗ ' + p)
            print('未通过，终止 ✗')
            return 1
        print('  ✓ 必需文件齐全（%d 项）' % len(REQUIRED))
        print('  ✓ 无 PDF / 密钥 / 安装包 / node_modules')

        os.makedirs(args.out, exist_ok=True)
        out_zip = os.path.join(args.out, '%s-%s.zip' % (PKG_NAME, VERSION))
        cnt = make_zip(src, out_zip)
        print()
        print('  已打包：%s' % out_zip)
        print('  %d 个文件 / %.0f KB' % (cnt, os.path.getsize(out_zip) / 1024))

        # 校验：解压后核心自检能否真跑（不需要浏览器的那几项）
        print()
        print('=== 验收：解压后跑核心自检 ===')
        ex = os.path.join(work, 'ex')
        os.makedirs(ex)
        with zipfile.ZipFile(out_zip) as z:
            bad = [i.filename for i in z.infolist() if not (i.flag_bits & 0x800)]
            if bad:
                print('  ✗ 有 %d 个文件名未标记 UTF-8' % len(bad))
                return 1
            z.extractall(ex)
        pkg = os.path.join(ex, PKG_NAME)
        import subprocess
        ok_all = True
        for label, cmd in [
            ('引擎独立运行', ['node', 'apps/linalg-lab/tools/verify-engine.mjs']),
            ('判题注册表', ['node', 'apps/linalg-lab/tools/verify-registry.mjs']),
            ('第二科目', ['node', 'apps/linalg-lab/tools/verify-calculus.mjs']),
            ('诊断覆盖率', ['node', 'apps/linalg-lab/tools/verify-diagnostics.mjs']),
            ('诊断准确性', ['node', 'apps/linalg-lab/tools/verify-diagnosis-accuracy.mjs']),
            ('插件 API 一致性', ['node', 'apps/linalg-lab/tools/verify-plugin-api.mjs']),
            ('信息量审计', ['node', 'apps/linalg-lab/tools/audit-coverage.mjs']),
            ('静态内容适配器', ['python3', 'engine-core/adapters/static-content/verify.py',
                            'apps/linalg-lab', '--allow-outside']),
        ]:
            r = subprocess.run(cmd, cwd=pkg, capture_output=True, text=True)
            ok = r.returncode == 0
            ok_all = ok_all and ok
            print('  %s %-16s %s' % ('✓' if ok else '✗', label,
                                     (r.stdout or r.stderr).strip().split('\n')[-1][:56]))
        print()
        if not ok_all:
            print('验收未通过 ✗')
            return 1
        print('全部通过 ✓ 解压即可复现；审查指南在最外层「给审查者的说明.md」')
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    raise SystemExit(main())
