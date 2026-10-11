#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比度基线采集（第六十五轮立 · 第六十六轮改为**自带目标与依赖自检** ✓）。

## 为什么改（审计方在它的环境里跑到 n=0、分位数全 None ✗）
- 老版**依赖调用方把参数传对** ✗（它给的是相对路径/错的 base ⇒ 一个产物都解析不到 ⇒ `n=0`）；
- 而 `n=0` **长得像结论**，其实是"**没跑成**" ✗ —— 那正是本项目一路在治的**假绿形态** ✓。

## 现在的三条纪律
1. **自带目标**：不给参数时，自己从 `engine-core/adapters/content-spec/manifest.json` 解析要测哪些产物 ✓
   （不依赖调用方传对 ✗）；给了参数就用参数，但**路径会先 `abspath`** ✓。
2. **取不到目标 ⇒ 明确原因 + `exit 2`** ✓（无浏览器 / 页面不在 / 一个可测文本都没有 ⇒ 都退 2 ✓），
   **绝不打印一串 `n=0` 的 JSON 冒充结论** ✗。
3. **逐字命令**写进 `--help` 与 docstring ✓，审计环境照抄即得同样的数 ✓。

用法（逐字 ✓）：
    cd 工作台/线代交互实验台/apps/linalg-lab
    python3 tools/contrast-baseline.py                 # 自带目标 ✓
    python3 tools/contrast-baseline.py --json          # 只输出 JSON（便于贴进 evidence ✓）
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))     # <repo>：tools→linalg-lab→apps→repo（**三级** ✓）
CS = os.path.join(REPO, 'engine-core', 'adapters', 'content-spec')
PROBE = os.path.join(HERE, 'contrast-probe.mjs')
MANIFEST = os.path.join(CS, 'manifest.json')
sys.path.insert(0, CS)
import checks_contrast as C                                          # 复用同一个比值实现（单一来源 ✓）

# **自带目标**：优先取"两站对照的真实页"（lab-L00-S*），不够再取 frag-L00-S* ✓
WANT_PREFIX = ('lab-L00-S', 'frag-L00-S')


def resolve_targets():
    """自己解析目标产物 ✓ —— 不依赖调用方传参 ✗。"""
    if not os.path.isfile(MANIFEST):
        return [], '找不到 manifest：%s' % MANIFEST
    mx = json.load(open(MANIFEST, encoding='utf-8'))
    pick = []
    for s in mx.get('sources') or []:
        for a in s.get('artifacts') or []:
            if str(a.get('id', '')).startswith(WANT_PREFIX):
                p = os.path.abspath(os.path.join(CS, a['path']))
                # manifest 里的 path 若不在 CS 下，再试"仓库外"的绝对写法 ✓
                if not os.path.isfile(p):
                    p2 = os.path.abspath(os.path.join(REPO, a['path']))
                    p = p2 if os.path.isfile(p2) else p
                pick.append((a['id'], p))
    return pick, None


def probe(path):
    """跑探针。返回 (ratios, env_reason)。**环境问题返回原因字符串** ✓，不返回空列表冒充结果 ✗。"""
    r = subprocess.run(['node', PROBE, 'file://' + path], capture_output=True, text=True, timeout=180)
    if r.returncode == 2:
        return None, ((r.stderr or '').strip().splitlines() or ['(探针无 stderr)'])[-1][:160]
    if r.returncode != 0:
        return None, '探针非 0 退出（%d）：%s' % (r.returncode, (r.stderr or '')[:120])
    try:
        data = json.loads(r.stdout)
    except Exception as e:
        return None, '探针输出不是 JSON：%s' % e
    out = []
    for it in data.get('items') or []:
        v = C.ratio(it.get('fg'), it.get('bg'))
        if v is not None:
            out.append(round(v, 2))
    return out, None


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = max(0, min(len(xs) - 1, int(round((p / 100.0) * (len(xs) - 1)))))
    return xs[k]


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith('--')]
    as_json = '--json' in sys.argv
    targets, err = ([(os.path.basename(a), os.path.abspath(a)) for a in argv], None) if argv else resolve_targets()
    if err:
        print('无法确定要测哪些产物：%s' % err, file=sys.stderr)
        return 2
    if not targets:
        print('无法确定要测哪些产物（manifest 里没有 lab-L00-S*/frag-L00-S*）', file=sys.stderr)
        return 2
    per, allv, env_reasons = {}, [], []
    for aid, path in targets:
        if not os.path.isfile(path):
            env_reasons.append('%s：文件不在（%s）' % (aid, path)); continue
        v, why = probe(path)
        if why:
            env_reasons.append('%s：%s' % (aid, why)); continue
        if not v:
            env_reasons.append('%s：没有可测文本（页面里没有 p/li/td/h1-h4/span/strong/em/a）' % aid); continue
        per[aid] = {'n': len(v), 'min': min(v), 'p10': q(v, 10), 'p50': q(v, 50), 'p90': q(v, 90), 'max': max(v)}
        allv += v
        if not as_json:
            print('  %-22s n=%-4d min=%-6s p10=%-6s p50=%-6s p90=%-6s max=%s'
                  % (aid, len(v), min(v), q(v, 10), q(v, 50), q(v, 90), max(v)))
    if not per:
        # **一个都没测成 ⇒ 退 2 + 原因** ✓（不许打印 n=0 冒充结论 ✗）
        print('没测成任何产物（环境不足，**不是结论** ✗）：', file=sys.stderr)
        for r in env_reasons[:8]:
            print('   – ' + r, file=sys.stderr)
        return 2
    overall = {'n': len(allv), 'min': min(allv), 'p10': q(allv, 10), 'p50': q(allv, 50),
               'p90': q(allv, 90), 'max': max(allv)}
    if not as_json:
        print('\n  **全体**：' + json.dumps(overall, ensure_ascii=False))
        if env_reasons:
            print('  （另有 %d 个产物没测成：%s）' % (len(env_reasons), '；'.join(env_reasons[:3])))
    print(json.dumps({'per_file': per, 'overall': overall,
                      'env_missing': env_reasons, 'threshold': C.MIN_RATIO,
                      'threshold_basis': 'WCAG 2.1 AA 正文 4.5:1（常数，非本语料分位数）'}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
