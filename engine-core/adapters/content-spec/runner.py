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
    python3 ... --explain [--check ID]     # 讲清每条判据"凭什么成立、怎么用"（交出逻辑链）
    python3 ... --json                     # 机器可读的判定结果（含证书），供别的 agent/工具消费
    python3 ... --baseline                 # 显式重算基线（回归检查的依据；手改基线=关掉检查）
    python3 ... --delegates                # 审计：门禁会替我执行哪些外部脚本（只读/超时/位置）
    python3 ... --scope repo|env           # 只跑仓库内可判的（CI）/ 只跑依赖环境的（本机）

设计原则（用户定的）：**不只是给 agent 一份规范，而是交出它发现与修正问题所需的逻辑链**。
所以每条检查的判据说明写在它自己的 docstring 里（--explain 直接读它，不另写一份说明），
失败时输出可操作的处置卡（结论/证据/缺陷所在/照着谁改/改法/泛化/验证命令）。
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


def pair_is_env(src, chk):
    """这一 (来源 × 检查) 组合是否**依赖仓库外环境**？

    两种依赖，缺一都会让判定变成「环境不足」：
      · 来源的产物在**仓库外**（`resolve: workspace`，例如站点快照）；
      · 检查本身要**真实浏览器**（evidence=render）。
    另外：委托（evidence=external）**不算**环境依赖——它跑的是声明路径上的脚本，
    仓库内的夹具脚本在任何机器上都能跑；仓库外的委托会因上一条被归到 env。
    """
    if chk.get('evidence') == 'render':
        return True
    return any(a.get('resolve') == 'workspace' for a in (src.get('artifacts') or []))


def run_all(only_source=None, only_check=None, scope=None):
    from common import resolve as _resolve      # 门的判据用它（与引擎同一套路径解析 ✓）
    """scope: None=全部 ｜ 'repo'=只跑仓库内可判的（CI 用）｜ 'env'=只跑依赖环境的"""
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
            if scope in ('repo', 'env'):
                is_env = pair_is_env(src, chk)
                if (scope == 'repo') == is_env:
                    continue
            want = chk.get('applies_to') or 'product'
            arts = [a for a in src['artifacts'] if a.get('kind', 'product') == want]
            fn = load_check(chk['fn'])
            checker_crash = False
            for art in arts:
                # **产物存在性的统一闸门**（第五十四轮 §1.1）：**环境事实不下放给检查** ✓
                # 产物不在位 ⇒ 这一条本来就无从判起 ⇒ 报「环境不足」 ✓
                # ⚠️ 门只挡"东西不在"（判据 = 文件是否存在 ✗）；
                #    **不挡"检查有 bug / 判错了"** ✓ —— 后者仍走下面的 try/except 与"真·不符" ✗。
                r = None
                # 判据 = "**在检查会用的那些基准下都找不到**" ✓（第五十四轮修正）：
                # 我第一版只看 BASE，结果本地多报 6 条"环境不足" ✗ —— 因为有些产物的
                # path 是相对**工作区根**的 ✓。所以把三个候选都试一遍，都不在才判环境不足 ✓。
                _p = None
                if art.get('path'):
                    for _b in (BASE, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
                               os.getcwd()):
                        _cand = _resolve(art, _b)
                        if os.path.exists(_cand):     # 文件**或目录**（kind: site 的产物就是目录 ✓——我第一版只认 isfile ✗，本地多报 6 条）
                            _p = _cand
                            break
                if art.get('path') and _p is None:
                    r = {'pass': None,
                         'reason': '环境不足：产物不在位（%s）' % art['path'],
                         'certificate': {'resolved_path': _p, 'exists': False}}
                try:
                    if r is None:
                        r = fn(art, src, BASE)
                except Exception as e:      # 第十八轮：单条检查崩了不许吞掉整轮
                    r = {'pass': None,
                         'reason': '检查器故障：%s: %s' % (type(e).__name__, str(e).splitlines()[0][:160]),
                         'certificate': {'checker_crash': type(e).__name__}}
                exp = ((m.get('expectations') or {}).get(chk['id']) or {}).get(art['id'])
                if exp is None and chk['id'] == 'render-capability':
                    exp = art.get('expect')          # 兼容旧位置
                out.append({'check': chk['id'], 'title': chk['title'],
                            'artifact': art['id'], 'kind': art.get('kind', 'product'),
                            'label': '%s · %s' % (art['id'], chk['id']),
                            'severity': chk.get('severity', 'gate'),
                            'evidence': chk.get('evidence'), 'expect': exp, **r,
                            'known_defect': _kd_map().get((chk['id'], art['id']))})
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
    # C2（第四十一轮）：证书必须落到**人读路径** —— 否则"有证据"只对 --json 的用户成立。
    cert = r.get('certificate')
    if cert:
        det = cert.get('detail') or {}
        env = cert.get('environment') or {}
        print('       · 证据（证书）：type=%s ｜ env=%s'
              % (cert.get('evidence_type', '?'),
                 '、'.join('%s=%s' % (k, v) for k, v in list(env.items())[:3]) or '—'))
        for k, v in list(det.items())[:4]:
            print('           %s = %s' % (k, str(v)[:80]))
    elif r.get('pass') is False:
        print('       · 证据（证书）：**缺失** —— 判红但无 certificate')


EVIDENCE_ENUM = ('structural', 'render', 'human', 'external')


def manifest_contract_problems(m):
    """C1：清单本身的契约。

    机制不用声明，**判据必须声明**——每条检查都要说清它凭什么敢下结论
    （structural 静态结构 / render 渲染量测 / human 需人眼 / external 委托外部脚本）。
    缺声明 = 拒绝运行：这样"这检查到底在测什么"不会变成一个没人回答的问题。
    """
    bad = []
    for c in m['checks']:
        ev = c.get('evidence')
        if ev not in EVIDENCE_ENUM:
            bad.append('检查 %s 未声明证据类型（应为 %s 之一）' % (c['id'], '/'.join(EVIDENCE_ENUM)))
    # C2：**未被证伪的检查不许进套件**——语料里必须至少有一个"它应当判红"的例子。
    # 依据是台账 M5（检测器没校准就用来判断：假阳性 21 处、同一个正则陷阱犯 3 次）。
    # 一条只会在好内容上通过的检查，无法区分"它没发现问题"和"它根本不看"。
    _KD = _kd_map()
    exp = m.get('expectations') or {}
    for c in m['checks']:
        if c.get('evidence') == 'human':
            continue          # human 类不给机器判定，谈不上"被证伪"；改由 how_to_check 兜底（见 checks_human）
        if not any(v == 'fail' for v in (exp.get(c['id']) or {}).values()):
            bad.append('检查 %s 在语料里**没有反例**（没有期望为 fail 的产物）：未证伪的检查不许进套件'
                       % c['id'])
    return bad


def evidence_summary(m):
    import collections as _c
    return dict(_c.Counter(c['evidence'] for c in m['checks']))


def explain(m, only_check=None):
    """`--explain`：把"这个判据凭什么成立、怎么用"讲出来。

    用户定的原则：**不只是给 agent 一份规范，而是交出它的逻辑链**。
    所以每条检查暴露三样东西：
      ① 判据的来源与理由（检查自己的 docstring——写检查时就写在里面，不另写一份）；
      ② 它在语料上的战绩（多少坏例被判红 / 多少好例保持绿 / 多少条不适用）；
      ③ 它需要哪些声明（manifest 里这条检查用到的字段）。
    """
    import collections, inspect
    for c in m['checks']:
        if only_check and c['id'] != only_check:
            continue
        tally = collections.Counter((m['expectations'].get(c['id']) or {}).values())
        print('══ %s ｜ %s' % (c['id'], c['title']))
        print('   证据类型：%s ｜ 严重度：%s ｜ 适用：%s'
              % (c['evidence'], c.get('severity', 'gate'),
                 '全部来源' if not c.get('sources') else '、'.join(c['sources'])))
        print('   战绩：坏例判红 %d ｜ 好例保持绿 %d ｜ 不适用 %d'
              % (tally['fail'], tally['pass'], tally['skip']))
        try:
            fn = load_check(c['fn'])
            doc = (inspect.getdoc(fn) or inspect.getdoc(__import__(c['fn'].split(':')[0])) or '').strip()
        except Exception as e:
            doc = '（读不到判据说明：%s）' % e
        if doc:
            print('   判据（为什么这样定、踩过什么坑）：')
            for line in doc.split('\n'):
                print('     ' + line.strip())
        print()
    print('提示：判据说明取自检查自己的 docstring——**写检查时写在里面**，不另写一份，避免两处不一致。')
    return 0


def as_json(m, results):
    """`--json`：机器可读的判定结果（供别的 agent/工具消费，不用解析人类可读的输出）。"""
    import collections
    out = {'sources': [s['id'] for s in m['sources']], 'checks': len(m['checks']),
           'evidence': evidence_summary(m), 'verdicts': []}
    for r in results:
        out['verdicts'].append({
            'check': r['check'], 'artifact': r['artifact'], 'evidence': r.get('evidence'),
            'verdict': _verdict(r), 'expect': r.get('expect'),
            'known_defect': r.get('known_defect'),
            'reason': r.get('reason', ''), 'certificate': r.get('certificate'),
            'advice': r.get('advice'),
        })
    out['tally'] = dict(collections.Counter(v['verdict'] for v in out['verdicts']))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if any('检查器故障' in (o.get('reason') or '') for o in out):
        sys.exit(3)      # 结构化声明：有检查器故障
    return 0 if out['tally'].get('fail', 0) == 0 else 1


def list_delegates(m):
    """`--delegates`：**审计**——门禁会替我执行哪些外部脚本？

    一个会在门禁里执行外部代码的系统，必须能一条命令答清这件事：
    脚本在哪、是否声明只读、超时多少、期望是什么、为什么委托它。
    缺 `read_only` 或 `timeout` 的委托会被标红（它们在运行时会被拒绝执行）。
    """
    rows, bad = [], 0
    for src in m['sources']:
        for a in src['artifacts']:
            if a.get('kind') != 'delegate':
                continue
            ro, to = a.get('read_only'), a.get('timeout')
            if not ro or not to:
                bad += 1
            rows.append((src['id'], a['id'], a['path'], '只读' if ro else '**未声明只读**',
                         ('%ss' % to) if to else '**未声明超时**'))
    print('门禁将执行 %d 个外部脚本：' % len(rows))
    print('  %-22s %-26s %-8s %-10s %s' % ('来源', '委托', '只读', '超时', '脚本'))
    for r in rows:
        print('  %-22s %-26s %-8s %-10s %s' % (r[0][:22], r[1][:26], r[3], r[4], r[2][:64]))
    if bad:
        print('\n✗ 有 %d 个委托缺 只读/超时 声明——运行时会**拒绝执行**（这是有意为之的守卫）' % bad)
        return 1
    print('\n全部委托都已声明 只读 + 超时 ✓（这是它们被允许执行的前提）')
    return 0


_KD_CACHE = None


def _kd_map():
    global _KD_CACHE
    if _KD_CACHE is None:
        _KD_CACHE = {(c, a): i for (c, a), i, _u in _known_defects()}
    return _KD_CACHE


def _known_defects():
    """已登记的消费者侧缺陷（第四类 known_defect）：**判 fail 但已登记 → 不算失败**。

    三个最小开关（缺一不可）：① 引用已登记缺陷 id；② 归属必须是 consumer（**引擎侧不许登记**）；
    ③ 必须有 unblock（谁、做什么、解封条件）。缺任一条 → 该条目**不生效**（回落到"失败"）。
    """
    import json as _j
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manifest.json')
    try:
        d = _j.load(open(p, encoding='utf-8'))
    except Exception:
        return []
    out = []
    for x in (d.get('discovered_defects') or []):
        ap = (x.get('applies_to') or {})
        if x.get('owner') == 'consumer' and x.get('unblock') and ap.get('check'):
            for a in (ap.get('artifacts') or []):
                out.append(((ap['check'], a), x['id'], x['unblock']))
    return out


def dump_certificates(results, out_dir):
    """C5（第四十一轮）：证书落盘 —— 文件名 = `<产物id>-<hash12>.json`（**不带时间戳**）。
    同 hash 覆盖同一文件 ⇒ 不无限增长；生成时间写进内容（generated_at）。
    ⚠️ `out_dir` 必须进 .gitignore，否则会脏工作树（边界）。
    """
    import hashlib, json, os, time
    os.makedirs(out_dir, exist_ok=True)
    n = 0
    for r in results:
        cert = r.get('certificate')
        if not cert:
            continue
        prod = r.get('artifact', 'unknown')
        h = hashlib.sha256(('%s|%s' % (prod, r.get('check', ''))).encode('utf-8')).hexdigest()[:12]
        path = os.path.join(out_dir, '%s-%s.json' % (prod.replace('/', '_'), h))
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump({'artifact': prod, 'check': r.get('check'),
                       'generated_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                       'certificate': cert}, fh, ensure_ascii=False, indent=1)
        n += 1
    return n


def skip_is_qualified(chk, art, m, r=None, actual=None):
    """**skip 必须有据**（第六十二轮立，第六十三轮修补洞 ✗）—— 判据是**三段式** ✓。

    ## 第六十二轮那个洞（审计方指出的 ✓）
    我上一版收敛成 `return bool(reason.strip())` ✗ —— 而 `reason` 是**"实际判定"的理由**，
    **不是"期望为什么是 skip"** ✗ ⇒ **期望 skip 而实际 fail 时，reason 必然非空 ⇒ 永远放行** ✗ ⇒
    **恰好漏掉第六十二轮那两条的形态**（而"占位 skip"正是要治的病 ✓）。
    **那等于"用兜底掩盖不一致"** ✗ —— 正是本项目一路在治的形态 ✓。

    ## 三段式（照要求 §2.1 ✓）
    ① **显式写了 `why`**（期望是 dict 且 `why` 非空）⇒ **有据** ✓；
    ② **期望 skip 但实际不是 skip** ⇒ **不是"有据"，是"未定性"** ✗ ——
       此时任何非空 reason **都是实际判定的理由** ✓，**证明不了"这条本来不适用"** ✗；
    ③ **期望与实际都是 skip** ⇒ 这时才轮到"**引擎有没有说不适用的理由**"（reason 非空 ✓）。
    """
    exp = ((m.get('expectations') or {}).get(chk['id']) or {}).get(art['id'])
    if isinstance(exp, dict):
        return bool(exp.get('why'))                     # ① ✓
    if actual is None:
        actual = _verdict(r or {})
    if actual != 'skip':
        return False                                    # ② ✓（这就是那个洞 ✓）
    return bool(((r or {}).get('reason') or '').strip())  # ③ ✓


def main():
    argv = sys.argv[1:]
    mode = 'report' if '--report' in argv else ('discover' if '--discover' in argv else 'selftest')
    quiet = '--quiet' in argv
    only_source = argv[argv.index('--source') + 1] if '--source' in argv else None
    only_check = argv[argv.index('--check') + 1] if '--check' in argv else None
    scope = argv[argv.index('--scope') + 1] if '--scope' in argv else None

    if '--baseline' in argv:
        return write_baseline(only_source)
    if '--explain' in argv or '--checks' in argv:
        return explain(load_manifest(), only_check)
    if '--delegates' in argv:
        return list_delegates(load_manifest())

    m, results = run_all(only_source, only_check, scope)
    if '--json' in argv:
        return as_json(m, results)
    problems = manifest_contract_problems(m)
    if problems:
        print('清单契约不成立（C1 证据类型 / C2 必须能被反证）：')
        for x in problems:
            print('  ✗ %s' % x)
        return 1
    if not quiet:
        print('=== %s ===' % m['title'])
        print('来源 %d ｜ 检查 %d ｜ 产物 %d ｜ 判定 %d 条 ｜ 模式 %s'
              % (len(m['sources']), len(m['checks']),
                 sum(len(s['artifacts']) for s in m['sources']), len(results), mode))
        ev = evidence_summary(m)
        print('证据类型：' + ' ｜ '.join('%s %d' % (k, v) for k, v in sorted(ev.items()))
              + '（human 类不计入全绿）')
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
        ok, fails, unset, known, env_skip = 0, [], [], [], 0
        undecided = []      # 第六十二轮：skip 但**没有据**（未定性）✗
        for r in results:
            # 第六十二轮：归一化期望 ✓ —— 期望可写成 dict（带 why），比对前取其 verdict；
            # 否则 dict != 'skip' 会被算成「环境不足」✗（我第一版就踩了）。
            if isinstance(r.get('expect'), dict):
                r['expect'] = r['expect'].get('verdict')
            actual = _verdict(r)
            if r['expect'] is None:
                unset.append(r)
                continue
            # **未定性的 skip**（第六十二轮）：skip 只允许"确认不适用"这一种意思 ✗
            if r['expect'] == 'skip':
                _chk = next((c for c in m['checks'] if c['id'] == r['check']), None)
                _art = next((a for a in (m.get('artifacts') or [])
                             if a.get('id') == r['artifact']), None) or {'id': r['artifact'], 'kind': r.get('kind', 'product')}
                if _chk and not skip_is_qualified(_chk, _art, m, r, actual):
                    undecided.append(r)
            if r['expect'] == actual:
                ok += 1
            elif actual == 'fail' and r.get('known_defect'):
                # 第四类（第 22~26 轮）：判 fail 但**已登记** → 不算失败、**必须可见** ✓
                known.append(r)
                if not quiet:
                    print('  ◇ %-40s 期望 %-4s 实际 %-4s  —— 已登记缺陷 %s（待消费者侧修）'
                          % (r['label'], r['expect'], actual, r['known_defect']))
            elif actual == 'skip':
                # **环境不足**（第五十三轮）：这次没条件比 ⇒ 既不通过、也不算"检查器坏了" ✗
                # 旧版把它并进 fails ⇒ 裸环境里"什么都没比"却报"检查器可能坏了"（退 1）✗
                env_skip += 1
                if not quiet:
                    print('  – %-40s 期望 %-4s 本次没条件比：%s'
                          % (r['label'], r['expect'], (r.get('reason') or '')[:70]))
            else:
                fails.append(r)
                if not quiet:
                    print('  ✗ %-40s 期望 %-4s 实际 %-4s  —— %s'
                          % (r['label'], r['expect'], actual, (r.get('reason') or '')[:80]))

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
            human = [r for r in results if r.get('evidence') == 'human']
            if human and not quiet:
                print('  ⚠ 另有 %d 条**需人工确认**（human 证据：机器不签字，不计入全绿）' % len(human))
            # 结构化协议行（与 NOT-COMPARED: 同一套做法）：单行、前缀固定、机器可读
            # **必须打在 return 之前** —— 否则永远执行不到（第二十七轮就栽在这）
        # **三态退出码 + 护栏**（第五十三轮 §1.1/§1.2）：
        # 护栏下限的取值与理由（写进 docstring ✓）：
        #   **真正比对过的条数 ok 不得低于"应能比的条数"的一半** ✗ ——
        #   应能比 = ok + env_skip + len(fails)。理由：裸环境里"几乎什么都没比"却报通过，
        #   比报红更危险（轮六 RX-01 那个先例 / C2 契约要防的正是这种形态 ✓）。
        _total_comparable = ok + env_skip + len(fails)
        _too_few = _total_comparable > 0 and ok < (_total_comparable / 2.0)
        if undecided:
            print('有 %d 条期望未定性 ✗ —— skip 只允许"确认不适用"这一种意思：'
                  '要么该检查的 applies_to 不含这个产物的 kind，要么写成 {"verdict":"skip","why":"…"}' % len(undecided))
            for r in undecided[:6]:
                print('    – %-40s · %s（skip 但无据 ✗）' % (r['label'], r.get('kind', '?')))
            return 2
        if known:
            print('KNOWN-DEFECTS: %d 项 | %s'
                  % (len(known),
                     '、'.join('%s（消费者侧）' % x for x in sorted({r['known_defect'] for r in known}))))
        _tally = '比对过 %d 条 ｜ 环境不足 %d 条 ｜ 真·不符 %d 条' % (ok, env_skip, len(fails))
        if fails:
            print('失败 %d 项 ✗  判定与期望不符（检查器可能坏了）  ｜ %s' % (len(fails), _tally))
            return 1
        if _too_few:
            print('本次真正比对过的条数不足（%d / 应能比 %d）⇒ 判"环境不足"，不许报通过 ✗  ｜ %s'
                  % (ok, _total_comparable, _tally))
            return 2
        if env_skip:
            print('本次有 %d 条没条件比（环境不足）—— 不是通过、也不是失败 ✗  ｜ %s' % (env_skip, _tally))
            return 2
        print('全部通过 ✓  检查器在 %d 条真实判定上与期望一致  ｜ %s' % (ok, _tally))
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
    _cert_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir, os.pardir, '.certificates')
    _n_cert = dump_certificates(results, _cert_dir)
    if _n_cert:
        print('证书已落盘：%d 份 → .certificates/' % _n_cert)
    print('检出 %d 项 ✗ —— 这是**被检出的真实缺陷**，不是检查器故障；处置卡见上' % len(bad))
    return 1


if __name__ == '__main__':
    sys.exit(main())
