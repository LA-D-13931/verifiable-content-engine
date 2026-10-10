#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内容规范域 runner：读 manifest → 在各来源的各产物上跑检查 → 汇总。

两种模式，用途不同（这是本条检查能被信任的关键）：

  · `--selftest`（默认）：**反证检查器本身**。manifest 为每个产物声明了 expect
    （坏例 fail、好例 pass）；只有当"实际判定 == 声明期望"全部成立时才算通过。
    也就是说：套件里这一项验证的是**检查器能抓**，而不是"内容是好的"。
    好处：真实坏例可以长期留作夹具（它变绿反而说明检查器坏了），
    同时「全部通过」这条主张不被破坏。

  · `--report`：报告**当前实际判定**，并在每一处失败后打印**可操作的处置卡**
    （结论 / 证据 / 定位 / 参照 / 修法 / 泛化 / 验证命令）。
    这是本域对「交给 agent 就能用」的实现：agent 只需要它已有的工具
    （read 看定位、grep 找参照、edit 改、bash 重跑验证），不需要新的抽象。

退出码（三态，与 verify-all.py 一致）：
    0 通过 ／ 1 失败 ／ 2 环境不足

用法：
    python3 engine-core/adapters/content-spec/runner.py [--selftest|--report] [--source ID] [--quiet]
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
                    'role': prod.get('role'),
                    'pair': prod.get('pair'),
                    **r,
                })
    return m, out


def print_advice(r):
    """打印处置卡：让人/agent 拿着就能动手，而不是只看到一个 fail。"""
    caps = ((r.get('advice') or {}).get('capabilities') or [])
    for a in caps:
        print('      ── 怎么修：%s' % a.get('title'))
        loc, ref = a.get('locate'), a.get('reference')
        if loc:
            print('       · 缺陷所在：    %s:%s  %s'
                  % (loc['path'], loc.get('lines', '?'), loc.get('what', '')))
        if ref:
            print('       · 照着谁改：    %s:%s  %s'
                  % (ref['path'], ref.get('lines', '?'), ref.get('what', '')))
        if a.get('fix_hint'):
            print('       · 改法：        %s' % a['fix_hint'])
        if a.get('generalize'):
            print('       · 还能往哪扩：  %s' % a['generalize'])
        print('       · 验证：        python3 %s --report'
              % os.path.relpath(os.path.abspath(__file__), os.getcwd()))


def main():
    argv = sys.argv[1:]
    mode = 'report' if '--report' in argv else 'selftest'
    quiet = '--quiet' in argv
    only = None
    if '--source' in argv:
        only = argv[argv.index('--source') + 1]

    m, results = run_all(only)
    if not quiet:
        print('=== %s ===' % m['title'])
        print('来源 %d 个 ｜ 检查 %d 条 ｜ %d 个产物 ｜ 模式 %s'
              % (len(m['sources']), len(m['checks']), len(results), mode))
        print('')

    if mode == 'selftest':
        ok = 0
        fails = []
        for r in results:
            actual = 'pass' if r['pass'] else 'fail'
            matched = (r['expect'] == actual)
            ok += matched
            if not matched:
                fails.append(r)
            if not quiet and not matched:
                print('  ✗ %-38s 期望 %-4s 实际 %-4s  —— %s'
                      % (r['label'], r['expect'], actual, r['reason']))
        if not quiet:
            print('  （%d 个产物按 manifest 的 expect 反证完毕）' % len(results))
            print('')
        if ok == len(results):
            print('全部通过 ✓  检查器在 %d 个真实产物上判定与期望一致（%d 坏例变红 / %d 好例保持绿）'
                  % (len(results), sum(1 for r in results if r['expect'] == 'fail'),
                     sum(1 for r in results if r['expect'] == 'pass')))
            return 0
        print('失败 %d 项 ✗  检查器的判定与夹具期望不符（检查器可能坏了）' % len(fails))
        return 1

    bad = [r for r in results if not r['pass']]
    for r in results:
        if r['pass'] and quiet:
            continue
        print('  %s %-38s %s' % ('✓' if r['pass'] else '✗', r['label'],
                                 'pass' if r['pass'] else 'fail —— ' + r['reason']))
        if not r['pass']:
            print_advice(r)
            print('')
    if not quiet:
        print('')
    if not bad:
        print('全部通过 ✓  %d 个产物都具备必需渲染能力' % len(results))
        return 0
    print('检出 %d 项 ✗ —— 这是**被检出的真实缺陷**，不是检查器故障；处置卡见上' % len(bad))
    return 1


if __name__ == '__main__':
    sys.exit(main())
