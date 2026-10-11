#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全貌图单一来源检查（第八轮 §3 建立；第九轮 §1 收窄"不适用"并加仓库自带记录）。

## 判据（三级，逐一收窄 —— 第九轮要求）
1. 仓库副本 `docs/全貌图/engine-audit-flow.html` **不在位** → **不适用**（exit 0）
   —— 这是**全新克隆**：连要检查的东西都没有，不是"检查通过"。
   打印 `NOT-COMPARED: <原因>`，由 `verify-all.py` 计入「本次未比较 N 项」。
2. 仓库副本在位、但它与**仓库自带的记录** `docs/全貌图/图.sha256` 不符 → **判红（exit 1）**
   —— **这条让检查在全新克隆里也能生效**（不需要 `.archify` 在不在）。
3. 仓库副本在位、记录一致，但 `.archify` 源图**不在位** → **环境不足（exit 2）**
   —— 此时是"**要跑而跑不成**"（源图在仓库外），不是"这件事不适用"。
   （第九轮审计方实测：旧版在这里报「不适用」+ exit 0，于是**副本被篡改成任意内容也永远是绿的**。）
4. 两者都在位 → 三向比对（源图 ↔ 副本 ↔ 记录）→ 全一致 exit 0，任一不符 exit 1。

## 它能发现什么、不能发现什么（第九轮 §1 第 3 条要求写清）
- **能**：仓库副本被改动（与记录比）；仓库副本与 `.archify` 源图不一致（两处漂移）；
  记录本身过期（与源图比）。
- **不能**：**两处同时被改动且记录被同步更新** —— 那是"故意的、成对的一致性"，
  任何基于自身记录的机制都发现不了；对此唯一的判据是**人**（或外部审计方）比对历史 revision。
  记录只在显式执行 `--update-record` 时更新，**不会自动跟着变**（这一点是刻意的）。

用法：
  python3 apps/linalg-lab/tools/check-figure-sync.py                 # 检查
  python3 apps/linalg-lab/tools/check-figure-sync.py --update-record # 用当前副本更新记录（改图后必跑）
退出码：0 一致 / 不适用 ｜ 1 不一致（图漂了）｜ 2 环境不足（副本在位、源图不在位）
"""
import glob
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
WS = os.path.dirname(os.path.dirname(REPO))          # 工作区根（.archify 在它下面）
IN_REPO = os.path.join(REPO, 'docs', '全貌图', 'engine-audit-flow.html')
RECORD = os.path.join(REPO, 'docs', '全貌图', '图.sha256')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_record():
    if not os.path.isfile(RECORD):
        return None
    txt = open(RECORD, encoding='utf-8').read().strip().split()
    return txt[0] if txt else None


def check_labels(path):
    """第二十四轮 §3：图里 **data-node-label 不许重复**（"复制节点忘改标签"的机械判据）。"""
    import re as _re
    h = open(path, encoding='utf-8').read()
    labels = _re.findall(r'data-node-label="([^"]*)"', h)
    # 空 label 是合法的（外层包装节点用它），只查**非空**标签的重复
    labels = [x for x in labels if x.strip()]
    dup = sorted({x for x in labels if labels.count(x) > 1})
    return dup


def main():
    argv = sys.argv[1:]
    print('=== 全貌图单一来源检查 ===')

    # ── 判据 1：仓库副本不在位 → 不适用（全新克隆），并让汇总能计数 ──
    if not os.path.isfile(IN_REPO):
        print('  – 不适用：仓库里没有 docs/全貌图/engine-audit-flow.html（全新克隆，连检查对象都没有）')
        print('NOT-COMPARED: 仓库副本不在位（全新克隆）')
        return 0

    if '--update-record' in argv:
        h = sha(IN_REPO)
        with open(RECORD, 'w', encoding='utf-8') as f:
            f.write('%s  engine-audit-flow.html\n' % h)
        print('  ✓ 已更新记录：%s（%s）' % (RECORD.replace(REPO + '/', ''), h[:16]))
        return 0

    # ── 判据 2：与仓库自带记录比（**这条在全新克隆里也生效**）──
    cur, rec = sha(IN_REPO), read_record()
    print('  仓库副本：sha256 %s ｜ %d 字节' % (cur[:16], os.path.getsize(IN_REPO)))
    if rec is None:
        print('  ✗ 仓库里没有 docs/全貌图/图.sha256（记录缺失）——无法在无源图时判断副本是否被改')
        return 1
    print('  仓库记录：sha256 %s' % rec[:16])
    if cur != rec:
        print('  ✗ **仓库副本与自带记录不一致** → 图被改动过（或记录过期）。')
        print('     改图后请跑：python3 apps/linalg-lab/tools/check-figure-sync.py --update-record')
        return 1

    # ── 判据 3：源图不在位 → 环境不足（不是不适用）──
    srcs = sorted(glob.glob(os.path.join(WS, '.archify', 'architecture-engine-audit-flow-*',
                                         'review-2', 'engine-audit-flow.html')))
    if not srcs:
        print('  – 环境不足：副本与记录一致，但 .archify 源图不在位（源图在仓库外）→ "要跑而跑不成"')
        print('     这不是"不适用"：副本本身可判，只是**无法与源图独立交叉验证**')
        return 2
    src = srcs[-1]

    # ── 判据 4：三向比对 ──
    s_src = sha(src)
    print('  源图（.archify，取最新）：sha256 %s ｜ %d 字节' % (s_src[:16], os.path.getsize(src)))
    if s_src != cur:
        print('  ✗ 源图与仓库副本不一致 —— 两处漂了（这正是 single-source 要治的病）')
        print('     修法：cp "<源图>" docs/全貌图/engine-audit-flow.html 再 --update-record')
        return 1
    dup = check_labels(IN_REPO)
    if dup:
        print('  ✗ 图里有重复的 data-node-label：%s（复制节点忘了改标签）' % dup)
        return 1
    print('  ✓ data-node-label 无重复（%d 个节点）' % len(open(IN_REPO, encoding='utf-8').read().split('data-node-label=')) )
    print('  ✓ 三向一致（源图 == 仓库副本 == 仓库记录）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
