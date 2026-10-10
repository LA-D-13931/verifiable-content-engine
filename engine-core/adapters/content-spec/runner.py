#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""内容规范域 runner：读 manifest → 在「产物 × 检查」上跑 → 汇总。

三种模式：

  · `--discover`：**标定期望用**。打印每个 (产物 × 检查) 的实际判定，不改任何文件。
    新检查先跑它、看清它到底抓到了什么，再把这些结论冻结成期望。
    （顺序很重要：先观察，再声明。反过来就成了"让检查通过"。）

  · `--selftest`（默认）：**反证检查器本身**。manifest 的 `expectations` 为每个
    (检查 × 产物) 声明了期望；只有"实际判定 == 声明期望"全部成立才算通过。
    套件里这一项验证的是**检查器能抓**，不是"内容是好的"。真实坏例因此可以长期
    留作夹具（它变绿反而说明检查器坏了），而「全部通过」不被破坏。

  · `--report`：报告**当前实际判定**，并在失败处打印**可操作的处置卡**
    （结论 / 证据 / 缺陷所在 / 照着谁改 / 改法 / 泛化 / 验证命令）。
    这是本域对「交给 agent 就能用」的实现：agent 用它已有的 read/grep/edit/bash
    即可闭环，不需要新的抽象。

退出码（三态，与 verify-all.py 一致）：0 通过 ／ 1 失败 ／ 2 环境不足

用法：
    python3 engine-core/adapters/content-spec/runner.py [--discover|--selftest|--report]
            [--source ID] [--check ID] [--quiet]
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))

#: 三态：True 通过 / False 失败 / None **不适用**。
#: 不适用必须自成一态：静态检查在"运行时生成 DOM"的产物上会在空集里通过，
#: 那叫假绿——所以判据明确返回 None，而不是 True。
_MARK = {'pass': '✓', 'fail': '✗', 'skip': '–'}


def _verdict(r):
    return 'skip' if r.get('pass') is None else ('pass' if r['pass'] else 'fail')


def load_manifest():
    with open(os.path.join(BASE, 'manifest.json'), encoding='utf-8') as f:
        return json.load(f)


def load_check(fn_ref):
    mod_name, _, fn_name = fn_ref.partition(':')
    sys.path.insert(0, BASE)
    return getattr(__import__(mod_name), fn_name)


def write_baseline(only_source=None):
    """重算基线（`--baseline`）：把每个产物当前的体量计数写进 baseline.json。

    **必须显式**：基线是"上次的测量"，回归检查靠它判断"少了没有"。
    顺手改基线等于把回归检查关掉——所以只有这条命令会写它，且它打印改了哪些产物。
    声明 `baseline_from` 的产物**跳过**：它的基线应当继承自另一个产物
    （突变体就是这样：基线 = "未突变前那一份"的计数）。
    """
    from common import resolve
    from checks_regression import metrics
    m = load_manifest()
    out, skipped = {}, []
    for src in m['sources']:
        if only_source and src['id'] != only_source:
            continue
        for art in src['artifacts']:
            if art.get('kind', 'product') != 'product':
                continue
            if art.get('baseline_from'):
                skipped.append(art['id'])
                continue
            p = resolve(art, BASE)
            if os.path.isfile(p):
                with open(p, encoding='utf-8', errors='replace') as f:
                    out[art['id']] = metrics(f.read())
    path = os.path.join(BASE, 'baseline.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'note': '由 runner.py --baseline 生成；手改它等于关掉回归检查',
                   'artifacts': out}, f, ensure_ascii=False, indent=2, sort_keys=True)
    print('基线已重算：%d 个产物 → %s' % (len(out), path))
    if skipped:
        print('  （跳过继承基线的产物 %d 个：%s）' % (len(skipped), '、'.join(skipped[:4])))
    return 0


def run_all(only_source=None, only_check=None):
    m = load_manifest()
    out = []
    for src in m['sources']:
        if only_source and src['id'] != only_source:
            continue
        for chk in m['checks']:
            if only_check and chk['id'] != only_check:
                continue
            # 检查可声明只适用于哪些来源（`sources` 缺省 = 全部）。
            # 需要这个字段是因为"产物级"不等于"所有产物"：人智站的两个页面模板与
            # 高数站的章节页虽然都是产物，但前者才有渲染器源码/数据源/样式来源这些声明。
            if chk.get('sources') and src['id'] not in chk['sources']:
                continue
            want = chk.get('applies_to') or 'product'
            arts = [a for a in src['artifacts'] if a.get('kind', 'product') == want]
            fn = load_check(chk['fn'])
            for art in arts:
                r = fn(art, src, BASE)
                exp = ((m.get('expectations') or {}).get(chk['id']) or {}).get(art['id'])
                if exp is None and chk['id'] == 'render-capability':
                    exp = art.get('expect')          # 兼容旧位置
                out.append({'check': chk['id'], 'title': chk['title'],
                            'artifact': art['id'], 'kind': art.get('kind', 'product'),
                            'label': '%s · %s' % (art['id'], chk['id']),
                            'severity': chk.get('severity', 'gate'), 'expect': exp, **r})
    return m, out


def print_advice(r):
    for a in ((r.get('advice') or {}).get('capabilities') or []):
        print('      ── 怎么修：%s' % a.get('title', a.get('capability', '')))
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
    mode = 'report' if '--report' in argv else ('discover' if '--discover' in argv else 'selftest')
    quiet = '--quiet' in argv
    only_source = argv[argv.index('--source') + 1] if '--source' in argv else None
    only_check = argv[argv.index('--check') + 1] if '--check' in argv else None

    if '--baseline' in argv:
        return write_baseline(only_source)

    m, results = run_all(only_source, only_check)
    if not quiet:
        print('=== %s ===' % m['title'])
        print('来源 %d ｜ 检查 %d ｜ 产物 %d ｜ 判定 %d 条 ｜ 模式 %s'
              % (len(m['sources']), len(m['checks']),
                 sum(len(s['artifacts']) for s in m['sources']), len(results), mode))
        print('')

    if mode == 'discover':
        for r in results:
            print('  %s %-52s %s' % (_MARK[_verdict(r)], r['label'],
                                     'pass' if r['pass'] else (r['reason'][:96] or '不适用')))
        print('')
        print('标定完成：%d 条判定（通过 %d / 失败 %d / 不适用 %d）。把这些结论按 (检查 × 产物) '
              '冻结成 manifest.expectations 后，再用 --selftest 反证。'
              % (len(results), sum(1 for r in results if _verdict(r) == 'pass'),
                 sum(1 for r in results if _verdict(r) == 'fail'),
                 sum(1 for r in results if _verdict(r) == 'skip')))
        return 0

    if mode == 'selftest':
        ok, fails, unset = 0, [], []
        for r in results:
            actual = _verdict(r)
            if r['expect'] is None:
                unset.append(r)
                continue
            if r['expect'] == actual:
                ok += 1
            else:
                fails.append(r)
                if not quiet:
                    print('  ✗ %-40s 期望 %-4s 实际 %-4s  —— %s'
                          % (r['label'], r['expect'], actual, r['reason'][:80]))
        if not quiet:
            print('  （%d 条按 manifest 的 expectations 反证完毕）' % len(results))
            print('')
        if unset:
            print('失败 %d 项 ✗  有 %d 条**没有声明期望**（语料没钉住：先跑 --discover 再冻结）'
                  % (len(fails) + len(unset), len(unset)))
            for r in unset[:4]:
                print('   - 缺期望：%s' % r['label'])
            return 1
        if not fails:
            nf = sum(1 for r in results if r['expect'] == 'fail')
            np_ = sum(1 for r in results if r['expect'] == 'pass')
            ns = sum(1 for r in results if r['expect'] == 'skip')
            print('全部通过 ✓  检查器在 %d 条真实判定上与期望一致（%d 条坏例变红 / %d 条好例保持绿'
                  '%s）' % (len(results), nf, np_,
                            ' / %d 条按不适用处理' % ns if ns else ''))
            return 0
        print('失败 %d 项 ✗  判定与期望不符（检查器可能坏了）' % len(fails))
        return 1

    bad = [r for r in results if r.get('pass') is False]
    for r in results:
        if r['pass'] and quiet:
            continue
        v = _verdict(r)
        print('  %s %-48s %s' % (_MARK[v], r['label'],
                                 'pass' if v == 'pass' else (r['reason'] if v == 'skip'
                                                             else 'fail —— ' + r['reason'])))
        if v == 'fail':
            print_advice(r)
            print('')
    if not quiet:
        print('')
    if not bad:
        print('全部通过 ✓  %d 条判定都通过' % len(results))
        return 0
    print('检出 %d 项 ✗ —— 这是**被检出的真实缺陷**，不是检查器故障；处置卡见上' % len(bad))
    return 1


if __name__ == '__main__':
    sys.exit(main())
