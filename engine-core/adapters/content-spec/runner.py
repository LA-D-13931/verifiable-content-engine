#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内容规范域 runner：读 manifest → 在各来源的各产物上跑检查 → 汇总。

两种模式，用途不同（这是本条检查能被信任的关键）：

  · `--selftest`（默认）：**反证检查器本身**。manifest 为每个产物声明了 expect
    （坏例 fail、好例 pass）；只有当"实际判定 == 声明期望"全部成立时才算通过。
    也就是说：套件里这一项验证的是**检查器能抓**，而不是"内容是好的"。
    好处：真实坏例可以长期留作夹具（它变绿反而说明检查器坏了），
    同时 19 项全绿这条主张不被破坏。

  · `--report`：报告**当前实际判定**（用来演示"当场抓到真实缺陷"）。
    坏例在修好之前会一直红——那是被检出的真实缺陷，不是检查器故障。

退出码（三态，与 verify-all.py 一致）：
    0 通过 ／ 1 失败（selftest 期望不符｜report 有未通过产物）／ 2 环境不足

用法：
    python3 engine-core/adapters/content-spec/runner.py [--selftest|--report] [--source ID]
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))


def load_manifest():
    with open(os.path.join(BASE, 'manifest.json'), encoding='utf-8') as f:
        return json.load(f)


def load_check(fn_ref):
    mod_name, _, fn_name = fn_ref.partition(':')
    sys.path.insert(0, BASE)
    mod = __import__(mod_name)
    return getattr(mod, fn_name)


def run_all(only_source=None):
    m = load_manifest()
    out = []
    for src in m['sources']:
        if only_source and src['id'] != only_source:
            continue
        for chk in m['checks']:
            fn = load_check(chk['fn'])
            for prod in src['products']:
                r = fn(prod, src, BASE)
                out.append({
                    'name': chk['id'],
                    'label': '%s · %s' % (src['id'], prod['id']),
                    'severity': chk.get('severity', 'gate'),
                    'expect': prod.get('expect'),
                    **r,
                })
    return m, out


def main():
    argv = sys.argv[1:]
    mode = 'report' if '--report' in argv else 'selftest'
    only = None
    if '--source' in argv:
        only = argv[argv.index('--source') + 1]

    m, results = run_all(only)
    print('=== %s ===' % m['title'])
    print('来源 %d 个 ｜ 检查 %d 条 ｜ 模式 %s'
          % (len(m['sources']), len(m['checks']), mode))
    print('')

    if mode == 'selftest':
        ok = 0
        for r in results:
            actual = 'pass' if r['pass'] else 'fail'
            matched = (r['expect'] == actual)
            ok += matched
            print('  %s %-34s 期望 %-4s 实际 %-4s%s'
                  % ('✓' if matched else '✗', r['label'], r['expect'], actual,
                     ('  —— ' + r['reason']) if r['reason'] else ''))
        print('')
        if ok == len(results):
            print('全部通过 ✓  检查器在真实坏例上变红、在正常产物上保持绿（%d/%d 符合预期）'
                  % (ok, len(results)))
            return 0
        print('失败 %d 项 ✗  检查器的判定与夹具期望不符（检查器可能坏了）' % (len(results) - ok))
        return 1

    bad = [r for r in results if not r['pass']]
    for r in results:
        print('  %s %-34s %s%s'
              % ('✓' if r['pass'] else '✗', r['label'],
                 'pass' if r['pass'] else 'fail',
                 ('  —— ' + r['reason']) if r['reason'] else ''))
    print('')
    if not bad:
        print('全部通过 ✓  当前声明的全部产物都具备必需渲染能力（%d 项）' % len(results))
        return 0
    print('检出 %d 项 ✗ —— 这是**被检出的真实缺陷**，不是检查器故障' % len(bad))
    return 1


if __name__ == '__main__':
    sys.exit(main())
