#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""安全地把实验块插入 lab-data.js。

为什么需要这个工具：上一轮我用「按行号切片重排」的脚本直接把 lab-data.js 写坏了，
而且当时没有先备份，最后只能整份重写。这个脚本把当时的教训固化成流程：

  1. 动手前先把 lab-data.js 复制成 lab-data.js.bak-<时间戳>
  2. 用「块边界自检」解析现有实验：每个块必须以 `    {` 开头、
     以 `    },` 结束，否则直接中止，绝不写入
  3. 新块按 id 排序后插入到「同章最后一个已有实验」之后；
     如果目标章节还不存在，就插到 `window.LABS = [` 之后
  4. 写回后再自检一遍：实验数量必须等于「原有数 + 新增数」，
     且 id 集合与预期完全一致；不一致就立刻回滚

用法：
    python3 tools/insert-labs.py new-labs.py

其中 new-labs.py 需要提供一个 NEW_LABS 列表（Python 字面量列表，元素是字符串，
每个字符串是一个完整的 JS 实验块，以 `    {` 开头、以 `    },` 结束）。
"""
import os
import re
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
DATA = os.path.join(SITE, 'assets', 'js', 'lab-data.js')


def die(msg):
    print('中止：%s' % msg)
    sys.exit(1)


def parse_labs(text):
    """把 lab-data.js 拆成 (头部, [(id, 块文本)], 尾部)。"""
    lines = text.split('\n')
    starts = []
    for i, l in enumerate(lines):
        m = re.match(r"^        id: '(\d+-\d+)',", l)
        if m:
            starts.append((i, m.group(1)))
    if not starts:
        die('一个实验都没解析到，文件可能已损坏')

    head_end = next((i for i, l in enumerate(lines) if l.startswith('window.LABS')), None)
    if head_end is None:
        die('找不到 window.LABS')
    # 从 window.LABS 之后找第一个单独的 `];`，那才是 LABS 的结束（CHAPTERS 的 `];` 在前面）
    tail_start = next((i for i in range(head_end + 1, len(lines)) if lines[i].strip() == '];'), None)
    if tail_start is None:
        die('找不到 window.LABS 的结束 ];')

    head = '\n'.join(lines[:head_end + 1])
    tail = '\n'.join(lines[tail_start:])

    # 下一个实验的 `    {` 行之前，可能夹着章注释与空行，需要往前跳过
    def block_end(next_brace):
        j = next_brace - 1
        while j > 0:
            t = lines[j].strip()
            if t == '' or t.startswith('/*'):
                j -= 1
                continue
            break
        return j + 1

    blocks = []
    for k, (ln, lid) in enumerate(starts):
        begin = ln - 1
        end = block_end(starts[k + 1][0] - 1) if k + 1 < len(starts) else block_end(tail_start)
        seg = lines[begin:end]
        while seg and not seg[-1].strip():
            seg.pop()
        if seg[0].strip() != '{':
            die('%s 的块没有以 `{` 开头（实际：%r）' % (lid, seg[0]))
        # 最后一个实验在源文件里可能写作 `    }`（后面紧跟 `];`），统一补上逗号
        if seg[-1].rstrip() == '    }':
            seg[-1] = '    },'
        if seg[-1].strip() != '},':
            die('%s 的块没有以 `},` 结束（实际：%r）' % (lid, seg[-1]))
        blocks.append((lid, '\n'.join(seg)))
    return head, blocks, tail


def lab_key(lid):
    a, b = lid.split('-')
    return (int(a), int(b))


def main():
    if len(sys.argv) < 2:
        die('用法：python3 tools/insert-labs.py new-labs.py')

    ns = {}
    with open(sys.argv[1], encoding='utf-8') as f:
        exec(compile(f.read(), sys.argv[1], 'exec'), ns)
    new_blocks = ns.get('NEW_LABS')
    if not new_blocks:
        die('new-labs.py 里没有 NEW_LABS')
    # 允许用 @@NL@@ 占位换行（方便在源码里书写长块）
    new_blocks = [b.replace('@@NL@@', '\n') for b in new_blocks]

    # 新块自检
    parsed_new = []
    for blk in new_blocks:
        blk = blk.rstrip('\n')
        if not blk.startswith('    {'):
            die('新块没有以 `    {` 开头：%r' % blk[:40])
        if not blk.endswith('    },'):
            die('新块没有以 `    },` 结束：%r' % blk[-40:])
        m = re.search(r"^        id: '(\d+-\d+)',", blk, re.M)
        if not m:
            die('新块里找不到 id：%r' % blk[:60])
        parsed_new.append((m.group(1), blk))

    text = open(DATA, encoding='utf-8').read()
    head, blocks, tail = parse_labs(text)
    old_ids = [lid for lid, _ in blocks]
    new_ids = [lid for lid, _ in parsed_new]

    # 备份
    stamp = time.strftime('%Y%m%d-%H%M%S')
    bdir = os.path.join(SITE, 'backups')
    os.makedirs(bdir, exist_ok=True)
    backup = os.path.join(bdir, 'lab-data.js.bak-' + stamp)
    shutil.copy2(DATA, backup)
    print('已备份 → %s' % os.path.basename(backup))

    # 合并 + 按课程顺序排序
    merged = dict(blocks)
    for lid, blk in parsed_new:
        if lid in merged:
            die('id %s 已存在' % lid)
        merged[lid] = blk
    order = sorted(merged, key=lab_key)

    # 重新生成：按章分组，章之间插注释
    out = [head]
    seen = None
    for lid in order:
        ch = lab_key(lid)[0]
        if ch != seen:
            seen = ch
            suffix = ' · 自由沙盒' if ch == 99 else ''
            out.append('    /* ---------- 第 %d 章%s ---------- */' % (ch, suffix))
        out.append(merged[lid])
    out.append(tail)
    result = '\n'.join(out) + '\n'

    # 写回前先自检一遍
    h2, b2, t2 = parse_labs(result)
    got = [lid for lid, _ in b2]
    if got != order:
        die('写回自检失败：id 序列不一致')
    if len(got) != len(old_ids) + len(new_ids):
        die('写回自检失败：数量 %d != %d + %d' % (len(got), len(old_ids), len(new_ids)))

    open(DATA, 'w', encoding='utf-8').write(result)
    print('已插入 %d 个实验：%s' % (len(new_ids), '、'.join(new_ids)))
    print('实验总数：%d → %d' % (len(old_ids), len(got)))
    print('（校验失败可从 %s 恢复）' % os.path.basename(backup))
    return 0


if __name__ == '__main__':
    sys.exit(main())
