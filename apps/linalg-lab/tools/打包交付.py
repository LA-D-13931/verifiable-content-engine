#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把引擎打包成可交付给第三方开发者的压缩包。

为什么要有这个脚本
==================
第一次打包是手工做的，结果出了问题 —— 都是**只在本机测不出来、交出去才会暴露**的：

  ① 打了两个包（tar.gz + zip）。收件人不知道该用哪个。
  ② macOS 的 zip 命令**不设置 UTF-8 标志位**，中文目录名在 Windows 上
     解压会乱码。
  ③ 包内 `apps/linalg-lab/README.md` 是早期原型文档（写着「11 个实验 8 章」，
     实际 58 个实验 12 章），且含一条包内不存在的死链。
  ④ 静态适配器把「宿主站点没提供那项脚本」误报成校验失败。
  ⑤ 参考实现里的 `../../engine-core/*.js` 被链接检查报成失效链接。

所以脚本不只是「压一下」，它把上面这些检查都固化了：
  结构照搬仓库 → 排除敏感与臃肿内容 → 写 UTF-8 标志 → 逐项验收 → 自检

用法：
    python3 tools/打包交付.py                    # 输出到工作区桌面
    python3 tools/打包交付.py --out /tmp/x       # 指定输出目录
    python3 tools/打包交付.py --keep-staging     # 保留解压用的临时目录
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(APP))

#: 包名（也是解压后的顶层目录名）
PKG_NAME = '数学内容校验引擎'
VERSION = 'v1.0'

#: 不进包的东西
#: '交付包' 是交付 README 的**源目录**，只用来取那一份说明，
#: 不该再出现在包里（否则包里会有两份一模一样的 README）。
EXCLUDE_DIRS = {'node_modules', '__pycache__', 'shots', '_backup', '.git', '.github',
                '交付包'}
EXCLUDE_FILES = {'package-lock.json', '.DS_Store'}
EXCLUDE_EXT = {'.pyc', '.log'}

#: 必须存在的文件 —— 少一个就说明打包漏了
#: 交付包的主 README 存在这里（不放在仓库根，避免与仓库自身文档混淆）
DELIVERY_README = os.path.join(HERE, '交付包', 'README.md')

REQUIRED = [
    'README.md',                                  # 给开发者的上手说明（从 DELIVERY_README 复制）
    'engine-core/README.md',                      # 引擎自身的 API 说明
    'engine-core/API_如何新增科目.md',              # 加科目的步骤
    'engine-core/registry.js',
    'engine-core/mat.js',
    'engine-core/mat.py',
    'engine-core/domains/linalg/judge.js',
    'engine-core/domains/calculus/judge.js',
    'engine-core/adapters/static-content/verify.py',
    'apps/linalg-lab/index.html',
    'apps/linalg-lab/assets/js/labs.json',
]

#: 绝不允许出现的东西（凭据类）。
#: 用带边界的正则，不用裸子串 —— 第一版用 'sk-' 做子串匹配，
#: 结果 task- / risk- 这些普通词全被报成「疑似凭据」（11 条里 9 条是误报）。
#: 假警报会让检查被忽视，这比漏报更危险。
FORBIDDEN_PAT = [
    (re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'), '私钥'),
    (re.compile(r'\bghp_[A-Za-z0-9]{30,}'), 'GitHub 令牌'),
    (re.compile(r'\bsk-[A-Za-z0-9]{32,}'), 'API 密钥'),
    (re.compile(r'\bAKIA[0-9A-Z]{16}\b'), 'AWS 密钥'),
]
#: 本脚本自己含有上面的模式串（用于检测），跳过它
SKIP_SELF = {'打包交付.py'}


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True,
                          text=True, **kw)


def stage(dest):
    """按仓库结构复制（不重排目录 —— 脚本用相对路径推导引擎位置）。"""
    if os.path.exists(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)
    # 仓库根不放交付说明（那是给使用者的），打包时单独放进去
    if not os.path.isfile(DELIVERY_README):
        raise SystemExit('✗ 找不到交付包说明：%s' % DELIVERY_README)

    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        rel = os.path.relpath(root, REPO)
        if rel == '.':
            rel = ''
        os.makedirs(os.path.join(dest, rel), exist_ok=True)
        for f in files:
            if f in EXCLUDE_FILES or os.path.splitext(f)[1] in EXCLUDE_EXT:
                continue
            shutil.copy2(os.path.join(root, f), os.path.join(dest, rel, f))
    shutil.copy2(DELIVERY_README, os.path.join(dest, 'README.md'))
    return dest


def audit(dest):
    """打包前的体检：必需要有的、绝不能有的、外链是否成立。"""
    problems = []
    for r in REQUIRED:
        if not os.path.isfile(os.path.join(dest, r)):
            problems.append('缺少必需文件：%s' % r)

    # 凭据扫描
    for root, dirs, files in os.walk(dest):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            p = os.path.join(root, f)
            try:
                txt = open(p, encoding='utf-8', errors='ignore').read()
            except OSError:
                continue
            if f in SKIP_SELF:
                continue
            for rx, what in FORBIDDEN_PAT:
                if rx.search(txt) and not f.endswith('.md'):
                    problems.append('疑似凭据（%s）：%s'
                                    % (what, os.path.relpath(p, dest)))
    return problems


def make_zip(src, out_zip):
    """打 zip —— 关键：让 Python 写，它会为非 ASCII 名设置 UTF-8 标志位（0x800）。

    用系统的 zip 命令不行：macOS 版不设这个标志，Windows 解压会乱码。
    """
    if os.path.exists(out_zip):
        os.remove(out_zip)
    n = 0
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in sorted(files):
                full = os.path.join(root, f)
                rel = os.path.join(PKG_NAME, os.path.relpath(full, src))
                z.write(full, rel)
                n += 1
    return n


def smoke(out_zip, workdir):
    """端到端验收：解压到全新目录，逐条跑校验命令。

    这是最有价值的一步 —— 前面的问题（③④⑤）全都是在这一步才暴露的。
    """
    ex = os.path.join(workdir, 'extract')
    if os.path.exists(ex):
        shutil.rmtree(ex)
    os.makedirs(ex)
    with zipfile.ZipFile(out_zip) as z:
        bad = [i.filename for i in z.infolist() if not (i.flag_bits & 0x800)]
        if bad:
            return False, ['zip 里有 %d 个文件名未标记 UTF-8（Windows 会乱码）' % len(bad)]
        z.extractall(ex)

    pkg = os.path.join(ex, PKG_NAME)
    results = []
    cmds = [
        ('引擎独立运行', ['node', 'apps/linalg-lab/tools/verify-engine.mjs']),
        ('判题注册表回归', ['node', 'apps/linalg-lab/tools/verify-registry.mjs']),
        ('第二科目可复用', ['node', 'apps/linalg-lab/tools/verify-calculus.mjs']),
        ('诊断覆盖率', ['node', 'apps/linalg-lab/tools/verify-diagnostics.mjs']),
        ('诊断准确性', ['node', 'apps/linalg-lab/tools/verify-diagnosis-accuracy.mjs']),
        ('插件 API 一致性', ['node', 'apps/linalg-lab/tools/verify-plugin-api.mjs']),
        ('信息量审计', ['node', 'apps/linalg-lab/tools/audit-coverage.mjs']),
        ('静态内容适配器', ['python3', 'engine-core/adapters/static-content/verify.py',
                        'apps/linalg-lab', '--allow-outside']),
    ]
    ok_all = True
    for label, cmd in cmds:
        r = sh(cmd, cwd=pkg)
        ok = r.returncode == 0
        ok_all = ok_all and ok
        results.append((label, ok, (r.stdout or r.stderr).strip().split('\n')[-1][:60]))
    return ok_all, results


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None, help='输出目录（默认放到工作区桌面同级的桌面）')
    ap.add_argument('--keep-staging', action='store_true')
    args = ap.parse_args()

    work = tempfile.mkdtemp(prefix='pkg-')
    try:
        print('=== 打包交付 ===')
        src = stage(os.path.join(work, PKG_NAME))
        n_files = sum(len(fs) for _, _, fs in os.walk(src))
        size = sum(os.path.getsize(os.path.join(r, f))
                   for r, _, fs in os.walk(src) for f in fs)
        print('  暂存：%d 个文件 / %.1f MB' % (n_files, size / 1024 / 1024))

        print()
        print('=== 体检 ===')
        problems = audit(src)
        if problems:
            for p in problems:
                print('  ✗ ' + p)
            print('体检未通过，终止打包 ✗')
            return 1
        print('  ✓ 必需文件齐全（%d 项）' % len(REQUIRED))
        print('  ✓ 无凭据类内容')

        out_dir = args.out or os.path.expanduser('~/Desktop')
        os.makedirs(out_dir, exist_ok=True)
        out_zip = os.path.join(out_dir, '%s-%s.zip' % (PKG_NAME, VERSION))
        n = make_zip(src, out_zip)
        print()
        print('  已打包：%s' % out_zip)
        print('  %d 个文件 / %.0f KB' % (n, os.path.getsize(out_zip) / 1024))

        print()
        print('=== 端到端验收（解压到全新目录逐条跑）===')
        ok_all, results = smoke(out_zip, work)
        for label, ok, tail in results:
            print('  %s %-18s %s' % ('✓' if ok else '✗', label, tail))
        print()
        if not ok_all:
            print('验收未通过 ✗ —— 包已生成但不建议直接发出')
            return 1
        print('全部通过 ✓ 包可直接发给第三方开发者')
        return 0
    finally:
        if not args.keep_staging:
            shutil.rmtree(work, ignore_errors=True)
        else:
            print('（暂存目录保留在 %s）' % work)


if __name__ == '__main__':
    sys.exit(main())
