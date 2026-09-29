#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""建主站只读快照（W3-1：迁移校验脚本时不动主站本体）。

为什么要快照
============
P3 要把主站（高数学习站）的三套校验脚本迁进引擎。迁移中需要反复跑
「原脚本」与「迁移后」做差分对照——如果直接在主站上跑，一旦某个工具
有写入行为（哪怕只是 Bug），主站就被改了，而「主站未被改动」正是
本项目唯一能自证清白的证据。

做法与取舍
==========
· **复制**而非软链接：软链接下写入会穿透到主站，复制则天然隔离。
· 只复制 `线代_两站对照/data/主站文件清单.tsv` 里登记的文件（431 个），
  而不是整棵目录树——清单是主站内容的权威口径，副本也随之可核对。
· 副本路径：`01_活工程/线代_两站对照/snapshot/`（与对照工具放在一起）。
· 快照带一份 `.snapshot.json` 记录来源与时间，便于日后核对。

用法：
    python3 tools/gen-snapshot.py            建/重建快照
    python3 tools/gen-snapshot.py --check    只核对快照是否与主站一致
"""
import hashlib
import json
import os
import shutil
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(APP))
WORKSPACE = os.path.dirname(os.path.dirname(REPO))

MAIN = os.path.join(WORKSPACE, '01_活工程', '高等数学学习站')
CONTRAST = os.path.join(WORKSPACE, '01_活工程', '线代_两站对照')
MANIFEST = os.path.join(CONTRAST, 'data', '主站文件清单.tsv')
SNAPSHOT = os.path.join(CONTRAST, 'snapshot')
META = os.path.join(SNAPSHOT, '.snapshot.json')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_manifest():
    """清单每行：相对路径 \\t 字节数 \\t sha256"""
    out = []
    with open(MANIFEST, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line.strip():
                continue
            parts = line.split('\t')
            if len(parts) != 3:
                continue
            rel, size, digest = parts
            out.append((rel, int(size), digest))
    return out


def main():
    check_only = '--check' in sys.argv
    if not os.path.isdir(MAIN):
        print('✗ 找不到主站目录：%s' % MAIN)
        return 2
    if not os.path.isfile(MANIFEST):
        print('✗ 找不到清单：%s' % MANIFEST)
        return 2

    entries = read_manifest()
    print('清单登记 %d 个文件' % len(entries))

    # ---- 先核对主站是否与清单一致（快照必须来自可信状态）----
    mismatch, missing = [], []
    for rel, size, digest in entries:
        src = os.path.join(MAIN, rel)
        if not os.path.isfile(src):
            missing.append(rel)
            continue
        if os.path.getsize(src) != size or sha256(src) != digest:
            mismatch.append(rel)
    if missing or mismatch:
        print('✗ 主站与清单不一致，拒绝建快照（先查清原因）：')
        for r in missing[:5]:
            print('   缺失 %s' % r)
        for r in mismatch[:5]:
            print('   改动 %s' % r)
        return 1
    print('✓ 主站与清单完全一致')

    if check_only:
        if not os.path.isdir(SNAPSHOT):
            print('✗ 快照不存在 —— 运行 python3 tools/gen-snapshot.py')
            return 1
        bad = []
        for rel, size, digest in entries:
            p = os.path.join(SNAPSHOT, rel)
            if not os.path.isfile(p) or sha256(p) != digest:
                bad.append(rel)
        if bad:
            print('✗ 快照与主站不一致：%d 个文件' % len(bad))
            for r in bad[:5]:
                print('   %s' % r)
            return 1
        print('✓ 快照与主站一致（%d 个文件）' % len(entries))
        return 0

    # ---- 复制（先写临时目录，成功后原子替换，避免半成品快照）----
    tmp = SNAPSHOT + '.tmp'
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    for rel, size, digest in entries:
        dst = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(MAIN, rel), dst)

    meta = {
        'source': MAIN,
        'manifest': MANIFEST,
        'files': len(entries),
        'created': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'note': '只读快照：迁移校验脚本时的对照基准，不用于日常开发。'
                '重建：python3 tools/gen-snapshot.py',
    }
    os.makedirs(tmp, exist_ok=True)
    with open(os.path.join(tmp, '.snapshot.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)

    if os.path.exists(SNAPSHOT):
        shutil.rmtree(SNAPSHOT)
    os.replace(tmp, SNAPSHOT)

    total = sum(os.path.getsize(os.path.join(SNAPSHOT, r)) for r, _, _ in entries)
    print('✓ 快照已建：%s' % SNAPSHOT)
    print('  %d 个文件 / %.1f MB' % (len(entries), total / 1024 / 1024))
    print('  来源：%s' % MAIN)
    return 0


if __name__ == '__main__':
    sys.exit(main())
