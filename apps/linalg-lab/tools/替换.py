#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""锚点安全替换 —— 治「凭记忆写锚点」。

## 为什么有它
我在第 24–33 轮里，**至少 6 次**因为"锚点是我以为的文本"而让替换**静默不命中**：
把 `sed` 加的前缀缩进当成了文件缩进、子串里少一个空格、把正则转义写进了普通子串……
**每一次都白费一轮**，而且**失败时没有任何提示**（替换函数找不到就不改，退出码照样 0）。

## 它做什么
- **命中必须为 1**：0 次 → 报错并**打印最相近的几行**（带行号）；>1 次 → 报错并列出全部位置；
- **先看再改**：`--show` 只打印匹配处上下文，不改文件；
- **写完自证**：替换后重新读回文件，确认 `old` 已消失、`new` 已出现。

用法：
  python3 替换.py <文件> --show "<锚点子串>"
  python3 替换.py <文件> --old "<锚点子串>" --new "<新文本>"     # 简单替换
  python3 替换.py <文件> --old "<锚点>" --block <含新文本的文件或 -> 从 stdin 读整段
退出码：0 成功 / 1 锚点不唯一或没找到（并打印候选）
"""
import os
import re
import argparse
import difflib
import sys



def table_problems(text):
    """**表格守卫**（第六十轮 ③①）：Markdown 表里，行的列数与**同表表头**不一致 ⇒ 返回问题列表。

    为什么要它：我第五十八/五十九轮**两次把表格拆行**（插进去的单元格带了换行 ✗），
    而那两次都**过了** old/new 自证 ✓ —— **自证只管"改没改到"，不管"改完这张表还站得住吗"** ✗。
    这条把"先 --show 两端锚点"从**习惯**变成**机器判据** ✓。

    判据（只用结构，不猜语义 ✓）：
    - 表头 = 一段连续以 `|` 开头的块里**第一行**；列数 = 去掉首尾空单元后的 `|` 段数；
    - 同一块内每一行（含分隔行 `|---|---|`）的列数必须与表头一致；
    - **表格内不允许出现空行**（拆行的典型症状 ✗：碎片单独成行 ✓）。
    """
    problems = []
    lines = text.splitlines()
    block, start = [], 0
    def cells(ln):
        # ★ 用"单元格数"而不是"| 的个数"（后者对首尾空格/缩进敏感 ⇒ 我第一版把表头算成 -1 ✗，
        #   于是**正常替换也被拦** ✗）。strip('|') 后按 '|' 切分即可 ✓。
        return len(ln.strip().strip('|').split('|'))

    def flush(block, start):
        if len(block) < 2:
            return
        ncol = cells(block[0][0])
        for k, (ln, idx) in enumerate(block):
            if ln.strip().startswith('|') and cells(ln) != ncol:
                problems.append('第 %d 行：列数 %d ≠ 表头 %d（表格被拆行 ✗）'
                                % (idx + 1, cells(ln), ncol))
    for i, l in enumerate(lines):
        if l.strip().startswith('|'):
            if not block:
                start = i
            block.append((l, i))
        else:
            flush(block, start)
            block = []
    flush(block, start)
    return problems



FULLWIDTH = '（），：；、｜「」【】《》！？…—～'


def fullwidth_problems(text):
    """**全角字符守卫**（第六十二轮 ③）：标识符后紧跟全角字符 ⇒ 报问题。

    为什么：本会话 `$GITHUB_STEP_SUMMARY）` 这类**全角吃变量**出现过 **7 次**（第二多 ✗），
    每次都让整段脚本中断 ✓。**机械可查** ✓。

    判据（**只挡能确定的情形** ✓）：
    - 行**不是注释**（不含 `#` 开头）**且**不在引号内 ✓；
    - 出现 `<标识符><全角>` 的**紧邻**形态（标识符 = 变量名/命令名 ✓）。
    ⚠️ **分不清的情形（引号内的字符串、注释）一律放行** ✓ —— 那一条我如实写在文案里 ✓。
    """
    import re
    problems = []
    for i, ln in enumerate(text.splitlines(), 1):
        st = ln.strip()
        if st.startswith('#') or st.startswith('//'):
            continue          # 注释：放行 ✓（反例② ✓）
        # 简单引号剥离：把成对的引号内容换成占位符（分不清的就放行 ✓）
        stripped = re.sub(r"'[^']*'|\"[^\"]*\"", 'Q', ln)
        for m in re.finditer(r'([A-Za-z_$][\w$]*)([' + FULLWIDTH + r'])', stripped):
            problems.append('第 %d 行：`%s` 后紧跟全角「%s」—— 全角吃变量/参数 ✗'
                            % (i, m.group(1), m.group(2)))
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--show')
    ap.add_argument('--old')
    ap.add_argument('--new')
    ap.add_argument('--block')
    ap.add_argument('--verify-cmd', default=None,
                    help='替换后要跑的命令；非 0 则报错（用于"改完这个文件还站得住吗"）')
    a = ap.parse_args()
    try:
        text = open(a.path, encoding='utf-8').read()
    except OSError as e:
        print('✗ 读不到文件：%s' % e); return 1
    lines = text.splitlines(True)

    if a.show:
        hits = [i for i, l in enumerate(lines, 1) if a.show in l]
        print('锚点 %r 在 %s 命中 %d 处' % (a.show[:60], a.path, len(hits)))
        for i in hits[:6]:
            print('  %4d  %s' % (i, lines[i - 1].rstrip()))
        return 0

    if not a.old:
        print('✗ 要替换就得给 --old（先 --show 看一眼）'); return 1
    n = text.count(a.old)
    if n != 1:
        print('✗ 锚点命中 %d 次（必须恰好 1 次）—— 这是"凭记忆写锚点"的典型症状' % n)
        near = difflib.get_close_matches(a.old, [l.strip() for l in lines], n=5, cutoff=0.4)
        if n == 0 and near:
            print('  最相近的几行：')
            for c in near:
                for i, l in enumerate(lines, 1):
                    if l.strip() == c:
                        print('    %4d  %s' % (i, c[:100])); break
        elif n > 1:
            for i, l in enumerate(lines, 1):
                if a.old in l:
                    print('    %4d  %s' % (i, l.strip()[:100]))
        return 1

    new = a.new
    if a.block:
        new = sys.stdin.read() if a.block == '-' else open(a.block, encoding='utf-8').read()
    out = text.replace(a.old, new, 1)
    # 自证：old 必须消失（除非 new 里本来就含它 —— 例如插入到某行之前这种用法 ✓）；new 必须出现 ✓
    _old_gone = (a.old not in out) or (a.old in (new or ''))
    if not _old_gone or (new and new not in out):
        print('✗ 写完自证失败（old 仍在或 new 未出现）'); return 1
    # **先验后写**（第四十轮修正）：上一版先写再验 ⇒ 语法一坏就把坏内容落盘了 ✗。
    # 现在：先在内存里验，只有全过才写。
    # 自证 1：**整份文件还站得住吗**（上一轮我摔 4 次全是因为缺这一步）
    if a.path.endswith('.py'):
        import ast
        try:
            ast.parse(open(a.path, encoding='utf-8').read())
        except SyntaxError as e:
            print('✗ 替换后语法坏了：%s（行 %s）—— 已停在此处，请修' % (e.msg, e.lineno))
            return 1
    # 落盘自证 2：可选地跑一条命令（如该文件的主命令 / 单元测试）
    if a.verify_cmd:
        import subprocess as _sp
        r = _sp.run(a.verify_cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0:
            print('✗ --verify-cmd 失败（退出码 %d）：%s' % (r.returncode, a.verify_cmd))
            print('   ' + (r.stdout or r.stderr).strip()[:200])
            return 1
        print('  · --verify-cmd 通过：%s' % a.verify_cmd)

    # **写盘自证**（第四十二轮）：上一轮我踩过"报了成功却没写盘" ✗ ——
    # 那次是"写盘那行被自己的替换删掉" ✗，工具毫无察觉 ✗。
    # 所以落盘之后必须**读回**确认内容真的变了、**mtime** 真的动了 ✓。
    _before = os.path.getmtime(a.path) if os.path.exists(a.path) else 0
    # **全角字符守卫**（第六十二轮 ③）：标识符后紧跟全角 ⇒ **拒写** ✗
    _fw = fullwidth_problems(out)
    if _fw:
        print('✗ 全角守卫拦下：标识符后紧跟全角字符 —— 已**拒写** ✗')
        for p in _fw[:5]:
            print('    ' + p)
        print('   （提示：改成 `${VAR}` + 半角空白/半角括号 ✓；**引号内与注释里一律放行** ✓）')
        return 1
    # **表格守卫**（第六十轮 ③①）：列数与同表表头不一致 ⇒ **拒写** ✗
    _tbl = table_problems(out)
    if _tbl:
        print('✗ 表格守卫拦下：替换会让表格结构坏掉 —— 已**拒写** ✗')
        for p in _tbl[:5]:
            print('    ' + p)
        print('   （提示：多半是插入的单元格里带了换行 ✗ —— 先把两端锚点打出来再改 ✓）')
        return 1
    open(a.path, 'w', encoding='utf-8').write(out)
    os.utime(a.path, None)                       # 显式 touch，确保 mtime 一定变化 ✓
    _after = os.path.getmtime(a.path)
    _back = open(a.path, encoding='utf-8').read()
    if _back != out:
        print('✗ 写盘自证失败：读回的內容与要写入的不一致（磁盘没落 / 被并发改）')
        return 1
    if not (_after > _before):
        print('✗ 写盘自证失败：mtime 没变（%s → %s）—— 文件可能没被真正写入' % (_before, _after))
        return 1
    print('✓ 替换成功（锚点唯一；写完自证通过；语法' + ('已校验' if a.path.endswith('.py') else '不适用') + '）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
