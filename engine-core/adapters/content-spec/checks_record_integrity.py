#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P8 记录完好性（第七十轮）—— "记录只许增" ✓（台账原话：声明的记录文件必须存在且**行数不减少** ✓）。

## 基线从哪来（这是本条的关键设计决定 ✓）
**随仓库提交的基线文件** `fixtures/record-baseline.json` ✓ —— 而不是"每次跑时快照" ✗。理由：
- 快照型**没有跨运行状态** ⇒ "减少了"根本判不出来 ✗；
- 随仓库提交的基线**可 diff、可复现、可审计** ✓（和 `mat-vectors.json`、`katex-allowlist.json` 同一套做法 ✓）。

## 判据
- 声明的记录文件**不在** ⇒ **红** ✓（"声明了却找不到"不是"不适用" ✗ —— 台账说的就是"必须存在" ✓）；
- 行数 **< 基线** ⇒ **红** ✓（证书带文件、当前行数、基线行数 ✓）；
- 行数 **≥ 基线** ⇒ **通过** ✓（**加行不许报** ✗ —— 记录只许增 ✓）。
"""
import json
import os

BASE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixtures', 'record-baseline.json')


def run(artifact, source, base):
    try:
        base_cfg = json.load(open(BASE_FILE, encoding='utf-8'))
    except Exception as e:
        return {'pass': None, 'reason': '不适用/环境不足：基线文件读不到（%s）' % e,
                'certificate': {'baseline_file': BASE_FILE}}
    records = base_cfg.get('records') or {}
    # 第七十二轮修：**产物级优先** ✓ —— 原来写成 source 优先 ✗ ⇒ 来源级声明会**盖住**产物级 ✓，
    # 于是 rec-short-bad 这个"坏例夹具"被判成 pass ✗（C2 的凭据就没了 ✓）。更具体的声明应当赢 ✓。
    decl = (artifact.get('record_integrity') or source.get('record_integrity')
            or {'files': list(records.keys())})
    files = decl.get('files') or list(records.keys())
    if not files:
        return {'pass': None, 'reason': '不适用：**没有声明记录文件**（未声明 ⇒ 不适用 ✓，不是通过 ✗）',
                'certificate': {'needs': 'declaration'}}
    checked = []
    # 第七十一轮修：**两个候选基准** ✓ —— 记录文件是"仓库相对路径"（如 engine-core/…）
    # 而调用方给的 base 是**产物基准**（content-spec/）⇒ 只按 base 解析会全判"文件不在" ✗（实测 34 条假红）。
    REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))          # checks_*.py 在 engine-core/adapters/content-spec/ ⇒ 上推四级 ✓
    for rel in files:
        p = os.path.abspath(os.path.join(base, rel))
        if not os.path.isfile(p):
            p2 = os.path.abspath(os.path.join(REPO, rel))
            p = p2 if os.path.isfile(p2) else p
        want = records.get(rel)
        if not os.path.isfile(p):
            return {'pass': False,
                    'reason': '声明的记录文件**不在**：%s（台账 P8：必须存在 ✓）' % rel,
                    'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                    'detail': {'file': rel, 'exists': False, 'baseline': want}}}
        cur = sum(1 for _ in open(p, encoding='utf-8'))
        checked.append({'file': rel, 'lines': cur, 'baseline': want})
        if want is not None and cur < want:
            return {'pass': False,
                    'reason': '记录**行数减少**：%s 现在 %d 行 < 基线 %d 行（记录只许增 ✓）' % (rel, cur, want),
                    'certificate': {'verdict': 'fail', 'evidence_type': 'structural',
                                    'detail': {'file': rel, 'lines': cur, 'baseline': want}}}
    return {'pass': True, 'reason': '', 'certificate': {'checked': checked}}
