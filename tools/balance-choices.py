#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""平衡辨析题的正确选项位置。

背景：为了防「位置规律」，所有辨析题的正解被统一放在第 3 位；
但这样一来「永远选第 3 个」又成了新的规律。这个工具把正解均匀分布到
3 个位置上（按 id 顺序轮流错开），并同步旋转 options 与 explains，
保证「第 i 个选项」永远对应「第 i 条解释」。

流程（每一步都有自检，任何一步失败就中止且不写入）：
  1. 备份 lab-data.js
  2. 定位每个 choice 任务的 options / explains / check 三块
  3. 校验：两数组长度相等且都为 3；正解能以 ✓ / ✗ 标记唯一识别
  4. 计算本次旋转量，原地重写这两个数组与 check.correct
  5. 写回后用 node --check 与 tools/check-lab.py 复验

用法：
    python3 tools/balance-choices.py [--dry-run]
"""
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
DATA = os.path.join(SITE, 'assets', 'js', 'lab-data.js')

TASK_RE = re.compile(r"^            \{ id: '([^']+)', text: '辨析")
ID_RE = re.compile(r"^        id: '(\d+-\d+)',")


def die(msg):
    print('中止：%s' % msg)
    sys.exit(1)


def element_text(line, first):
    """从一行里取出字符串字面量。first=True 时该行还带 `options: [` 之类的前缀。"""
    if first:
        idx = line.index("'")
        s = line[idx + 1:]
    else:
        s = line.lstrip()
        if not s.startswith("'"):
            return None
        s = s[1:]
    # 去掉结尾的 '], 或 ',
    s = re.sub(r"'\],?\s*$", "", s)
    s = re.sub(r"',\s*$", "", s)
    return s


def main():
    dry = '--dry-run' in sys.argv
    lines = open(DATA, encoding='utf-8').read().split('\n')

    # 先按 id 行把文件切成「每个实验的区间」，
    # 再在每个区间里找 choice 任务 —— 这样同一实验里的第二道题也不会漏
    lab_starts = []
    for i, l in enumerate(lines):
        m = ID_RE.match(l)
        if m:
            lab_starts.append((i, m.group(1)))
    if not lab_starts:
        die('没有找到任何实验 id 行')

    tasks = []
    for k, (start, lab_id) in enumerate(lab_starts):
        end = lab_starts[k + 1][0] if k + 1 < len(lab_starts) else len(lines)
        i = start
        while i < end:
            mt = TASK_RE.match(lines[i])
            if not mt:
                i += 1
                continue
            tid = mt.group(1)
            j = i
            oi = ei = ci = None
            while j < end:
                if 'options: [' in lines[j] and oi is None:
                    oi = j
                if 'explains: [' in lines[j] and ei is None:
                    ei = j
                if "type: 'choice'" in lines[j]:
                    ci = j
                    break
                j += 1
            if oi is None or ei is None or ci is None:
                die('%s 任务 %s 找不到 options / explains / check' % (lab_id, tid))
            tasks.append({'lab': lab_id, 'task': tid, 'oi': oi, 'ei': ei, 'ci': ci})
            i = ci + 1

    if not tasks:
        die('没有找到任何 choice 任务')

    # 逐个任务：解析 → 计算旋转 → 原地重写
    changed = 0
    new_positions = []
    for k, t in enumerate(tasks):
        oi, ei, ci = t['oi'], t['ei'], t['ci']
        if ei <= oi or ci <= ei:
            die('%s 任务 %s 的三块顺序异常（options %d / explains %d / check %d）'
                % (t['lab'], t['task'], oi, ei, ci))

        # --- 解析 options ---
        opts = []
        for row in range(oi, ei):
            txt = element_text(lines[row], row == oi)
            if txt is None:
                die('%s 任务 %s 的 options 第 %d 行不是字符串' % (t['lab'], t['task'], row + 1))
            opts.append(txt)
        # --- 解析 explains ---
        exps = []
        for row in range(ei, ci):
            txt = element_text(lines[row], row == ei)
            if txt is None:
                die('%s 任务 %s 的 explains 第 %d 行不是字符串' % (t['lab'], t['task'], row + 1))
            exps.append(txt)

        if len(opts) != len(exps):
            die('%s 任务 %s 的 options(%d) 与 explains(%d) 数量不一致'
                % (t['lab'], t['task'], len(opts), len(exps)))
        n = len(opts)
        if n < 2:
            die('%s 任务 %s 只有一个选项' % (t['lab'], t['task']))

        # --- 找当前正解：以 ✓ 开头的那条 ---
        marks = [idx for idx, e in enumerate(exps) if e.strip().startswith('✓')]
        if len(marks) != 1:
            die('%s 任务 %s 的 explains 里有 %d 条以 ✓ 开头（应为 1）'
                % (t['lab'], t['task'], len(marks)))
        cur = marks[0]

        # --- 目标位置：按顺序轮流错开，尽量均匀 ---
        target = k % n
        # 左移 k_rot 位后，原下标 i 落在 (i - k_rot) mod n。
        # 要让原下标 cur 落到 target，需要 (cur - k_rot) ≡ target，即 k_rot = (cur - target) mod n。
        k_rot = (cur - target) % n
        if k_rot == 0:
            new_positions.append(cur)
            continue

        new_opts = opts[k_rot:] + opts[:k_rot]
        new_exps = exps[k_rot:] + exps[:k_rot]
        # 左移 k_rot 位后，原来在下标 i 的元素落到 (i - k_rot) mod n
        new_correct = (cur - k_rot) % n
        assert new_correct == target, (t['lab'], t['task'], cur, target, k_rot, new_correct)
        assert new_exps[new_correct].strip().startswith('✓'), (t['lab'], t['task'])

        # --- 重写 options 块（行数不变）---
        lines[oi] = re.sub(r"\[\s*'.*$", "['" + new_opts[0] + "',", lines[oi])
        for r in range(1, len(opts)):
            row = oi + r
            indent = re.match(r'^(\s*)', lines[row]).group(1)
            tail = "']," if r == len(opts) - 1 else "',"
            lines[row] = indent + "'" + new_opts[r] + tail
        # --- 重写 explains 块 ---
        lines[ei] = re.sub(r"\[\s*'.*$", "['" + new_exps[0] + "',", lines[ei])
        for r in range(1, len(exps)):
            row = ei + r
            indent = re.match(r'^(\s*)', lines[row]).group(1)
            tail = "']," if r == len(exps) - 1 else "',"
            lines[row] = indent + "'" + new_exps[r] + tail
        # --- check.correct ---
        lines[ci] = re.sub(r"correct: \d+", "correct: %d" % new_correct, lines[ci])

        new_positions.append(new_correct)
        changed += 1

    print('共 %d 道辨析题，本次调整 %d 道' % (len(tasks), changed))
    dist = {}
    for p in new_positions:
        dist[p] = dist.get(p, 0) + 1
    print('调整后正解位置分布：', dict(sorted(dist.items())))

    if dry:
        print('（--dry-run，未写入）')
        return 0

    stamp = time.strftime('%Y%m%d-%H%M%S')
    bdir = os.path.join(SITE, 'backups')
    os.makedirs(bdir, exist_ok=True)
    backup = os.path.join(bdir, 'lab-data.js.bak-' + stamp)
    shutil.copy2(DATA, backup)
    open(DATA, 'w', encoding='utf-8').write('\n'.join(lines))
    print('已写入（备份：%s）' % os.path.basename(backup))

    # 复验：语法 + 数据校验
    r = subprocess.run(['node', '--check', DATA], capture_output=True, text=True)
    if r.returncode != 0:
        shutil.copy2(backup, DATA)
        die('node --check 失败，已回滚：%s' % r.stderr.strip()[:200])
    r = subprocess.run([sys.executable, os.path.join(HERE, 'check-lab.py')],
                       capture_output=True, text=True, cwd=SITE)
    print(r.stdout.strip().split('\n')[-1])
    if r.returncode != 0:
        shutil.copy2(backup, DATA)
        die('check-lab.py 未通过，已回滚')
    return 0


if __name__ == '__main__':
    sys.exit(main())
