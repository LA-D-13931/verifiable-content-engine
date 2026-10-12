#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI workflow 自身的守卫（审查发现第 2 件 ✓）。

## 它治什么 ✓
实测：`verify-all.py` 里**提及 yaml 0 次** ⇒ **没有任何东西校验 `verify.yml` 自己能不能跑** ✗
—— 而我第 81 轮也如实说过"本机无 pyyaml ⇒ 我没能校验 YAML，让 CI 自己判"✗ ⇒ 本条就是补那个守卫 ✓。

## 判据（**只用标准库** ✓，不引第三方 ✓）
(甲) **顶层键**：必须有 `name:` / `on:` / `jobs:` ✓；
(乙) **触发器**：`on:` 下必须有 `push` / `pull_request` / `workflow_dispatch` **三个** ✓；
(丙) **步骤名集合与一份期望清单一致** ✓ —— 步骤**增减**必须改这份清单 ⇒ **显式** ✓（不许静默增减 ✗）；
(丁) 缩进只用空格、无 TAB ✓。

## ⚠️ 边界（写进注释**也印在输出里** ✓）
**只验"结构"，不验"YAML 语法本身"** ✗ —— 语法要真解析器（pyyaml ✓，本机没有 ✗）；
⇒ 本判据绿 **不等于** workflow 能跑 ✓；能跑与否由 **CI 自己**判 ✓（那条路仍在 ✓）。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
WF = os.path.join(REPO, '.github', 'workflows', 'verify.yml')

# **期望清单**（显式 ✓）：改 workflow 的步骤就必须改这里 ⇒ 改动有据可查 ✓
EXPECTED_TRIGGERS = {'push', 'pull_request', 'workflow_dispatch'}
EXPECTED_STEPS = {
    # ⚠️ 只列 **YAML 里真有的** 步骤 ✓ —— `Set up job` / `Post Run …` / `Complete job` 是 **GitHub 注入的** ✗
    # （它们不在文件里 ⇒ 拿它们当期望必然假红 ✓ —— 我第一版就栽在这 ✓）。
    'Run actions/checkout@v4', 'Run actions/setup-node@v4', 'Run actions/setup-python@v5',
    '依赖（puppeteer-core 等）', '引擎套件 --all（只跑 + 留证；判成败在下一步）',
    '汇总（always()：这一步必跑，结论自带原因）', '留证（artifact：让 agent 也读得到原因）',
    '汇总落文件（P7 · 让 agent 也读得到 Summary）', '提交 Summary（agent 用普通 git 就能读）',
}


def main():
    if not os.path.isfile(WF):
        print('ENV_INSUFFICIENT: 找不到 %s ⇒ **没验成**（不是失败 ✓）' % WF)
        return 2
    lines = open(WF, encoding='utf-8').read().splitlines()
    bad = []
    for i, l in enumerate(lines, 1):
        if '\t' in l:
            bad.append('%d 行有 TAB（YAML 只许空格 ✓）' % i)
    top = [l.split(':')[0].strip() for l in lines if l and not l.startswith(' ') and ':' in l]
    for k in ('name', 'on', 'jobs'):
        if k not in top:
            bad.append('顶层缺 `%s:`' % k)
    # 触发器（on: 之后、jobs: 之前的缩进行 ✓）
    try:
        a = next(i for i, l in enumerate(lines) if l.startswith('on:'))
        b = next(i for i, l in enumerate(lines) if l.startswith('jobs:'))
    except StopIteration:
        a = b = None
    trig = set()
    if a is not None and b is not None:
        for l in lines[a + 1:b]:
            m = re.match(r'^  ([A-Za-z_]+):', l)
            if m:
                trig.add(m.group(1))
    missing = EXPECTED_TRIGGERS - trig
    extra = trig - EXPECTED_TRIGGERS
    if missing:
        bad.append('触发器缺：%s（期望三个都在 ✓）' % '、'.join(sorted(missing)))
    if extra:
        bad.append('触发器多出未登记：%s（加了就要改期望清单 ✓）' % '、'.join(sorted(extra)))
    # 步骤名
    steps = set()
    for i, l in enumerate(lines):
        m = re.match(r'^\s*- name:\s*(.+?)\s*$', l)
        if m:
            steps.add(m.group(1))
        elif l.strip().startswith('- uses:'):
            steps.add('Run ' + l.strip().split('- uses:')[1].strip())
    miss_s = EXPECTED_STEPS - steps
    extra_s = steps - EXPECTED_STEPS
    if miss_s:
        bad.append('步骤缺：%s' % '、'.join(sorted(miss_s))[:200])
    if extra_s:
        bad.append('步骤多出未登记：%s（加了就要改期望清单 ✓）' % '、'.join(sorted(extra_s))[:200])
    print('  workflow = %s ｜ 触发器 %d 个 ｜ 步骤 %d 个 ｜ 期望清单 %d 个'
          % (os.path.basename(WF), len(trig), len(steps), len(EXPECTED_STEPS)))
    print('  ⚠️ 边界：**只验结构，不验 YAML 语法本身** ✗ —— 绿 ≠ 能跑 ✓（能跑与否交给 CI ✓）')
    if bad:
        print('✗ workflow 结构问题（%d 条）：' % len(bad))
        for x in bad:
            print('    · ' + x)
        return 1
    print('  ✓ 结构守卫通过（顶层键 / 三触发 / 步骤清单一致 / 无 TAB ✓）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
