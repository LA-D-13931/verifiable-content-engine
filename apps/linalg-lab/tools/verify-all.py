#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键复现：把本引擎的全部自检跑一遍，给出汇总表。

为什么要有这个脚本：本项目的核心主张是「可复现」。但自检分散在 12 个脚本里，
评审者需要一份清单才知道该敲哪些命令。这个脚本把清单变成一条命令，
并且**用退出码表达结论**——可以直接接进 CI，也可以现场演示。

用法：
    python3 tools/verify-all.py                  # 离线部分（只要 Python 3 与 Node）
    python3 tools/verify-all.py --with-browser   # 另加需要 puppeteer-core 与 Edge/Chrome 的三项
    python3 tools/verify-all.py --with-adapter   # 另加需要主站快照的静态适配器差分对照
    python3 tools/verify-all.py --all            # 以上全部

退出码：
    0  **本档**全部通过（未选择的项不算在内，会在末尾如实列出）
    1  有失败项
    2  环境不满足（缺 Node、缺依赖、缺快照）——**不算通过**，也不算代码失败

两种"没跑"必须分开，它们是**不同性质**的事（RX-01）：
    · 未选择（not_selected）：我没要求跑（缺 --with-browser / --with-adapter / --all）。
      这是**刻意的子集**，不算失败、不算环境不足，但**必须在末尾列出来**。
    · 环境不足（environment）：我要求跑了，但环境不满足（缺依赖 / 缺快照 / 超时 /
      子进程用退出码 2 自己声明"我因环境原因退出"）。→ 退出码 2。

汇总的硬规则（E1 的教训）：
    **只要存在"环境不足"项，就禁止打印「全部通过」**——改为「不可完整判定（N 项环境不足）」。
    曾经的行为是：跳过 7 项、照样打印「全部通过」、照样 return 0，
    于是"想让它绿，最省事的办法是少验"（激励方向错误）。跳过 ≠ 通过，这条在聚合层也要成立。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from paths import APP as SITE, ENGINE, REPO, WORKSPACE as _WS   # noqa: E402

PY = sys.executable

# (分组, 名称, 命令, 需要的能力)
CHECKS = [
    ('矩阵原语', 'Python 侧自检', [PY, os.path.join(ENGINE, 'mat.py')], None),
    ('矩阵原语', 'JS 侧与 Python 一致', ['node', 'tools/verify-mat.mjs'], None),
    ('矩阵原语', '两侧 + 生成物最新', [PY, 'tools/verify-mat.py'], None),
    ('矩阵原语', '独立裁决（精确有理数复算）', ['node', 'tools/audit-matrix-exact.mjs'], None),
    ('内容', '内容规范与缓存指纹', [PY, 'tools/check-lab.py'], None),
    ('内容', 'lab-data.js 可无损重建', ['node', 'tools/verify-labs.mjs'], None),
    ('引擎', '无浏览器跑完全部任务', ['node', 'tools/verify-engine.mjs'], None),
    ('引擎', '判题注册表回归', ['node', 'tools/verify-registry.mjs'], None),
    ('引擎', '第二科目复用同一接口', ['node', 'tools/verify-calculus.mjs'], None),
    ('引擎', '诊断覆盖率', ['node', 'tools/verify-diagnostics.mjs'], None),
    ('引擎', '诊断指向的失败条件正确', ['node', 'tools/verify-diagnosis-accuracy.mjs'], None),
    ('引擎', '插件 API 边界', ['node', 'tools/verify-plugin-api.mjs'], None),
    ('引擎', '引擎层边界（学科概念不得进引擎层）', ['node', 'tools/verify-boundary.mjs'], None),
    ('引擎', '零第三方依赖（引擎本体只用标准库）', ['node', 'tools/verify-no-deps.mjs'], None),
    ('文档', '材料互引不得用行号（改用锚点）', [PY, 'tools/check-anchor-refs.py'], None),
    ('文档', '全貌图单一来源（.archify 源图 == 仓库副本）', [PY, 'tools/check-figure-sync.py'], None),
    ('文档', '打印跳过却 exit 0 的位置必须被判定（批次 C 元检查）',
     [PY, 'tools/check-skip-exit.py'], None),
    ('引擎', '逐类型信息量审计', ['node', 'tools/audit-coverage.mjs'], None),
    ('引擎', '判据区分力审计（抓恒真判据）', ['node', 'tools/audit-tautology.mjs'], None),
    ('浏览器', '冒烟（控制台无错误）', ['node', 'tools/smoke.mjs'], 'browser'),
    ('浏览器', '8 组主题对比度', ['node', 'tools/verify-themes.mjs'], 'browser'),
    ('浏览器', '真实拖拽与判题抽查', ['node', 'tools/verify-actions.mjs'], 'browser'),
    ('浏览器', '可视化页样例与内联引擎', ['node', 'tools/verify-visual.mjs'], 'browser'),
    ('静态适配器', '原脚本 vs 适配器差分', [PY, 'tools/verify-static-adapter.py'], 'adapter'),
    # 内容规范域（第三个域）。这一项**反证检查器本身**：真实坏例必须被抓、正常产物必须保持绿。
    # 所以真实坏例可以长期留作夹具 —— 它变绿反而说明检查器坏了。
    ('内容规范', '真实坏例与突变体必须被抓（仓库内夹具，CI 可跑）',
     [PY, os.path.join(ENGINE, 'adapters', 'content-spec', 'runner.py'), '--selftest', '--scope', 'repo'], None),
    ('内容规范', '站点夹具 / 渲染量测 / 委托（依赖仓库外环境）',
     [PY, os.path.join(ENGINE, 'adapters', 'content-spec', 'runner.py'), '--selftest', '--scope', 'env'],
     'env-fixtures'),
]

PASS_MARKS = ('全部通过', '✓')

#: **结构化**的环境信号：子进程以退出码 2 退出 = 它自己声明"我因环境原因退出"。
#: 这是首选判据——**不靠文案**，所以既不会漏（文案改了照样认），也不会误伤
#: （内容失败应当用退出码 1）。审查方实测：11 处 `process.exit(2)` 的文案全部未命中下面的白名单，
#: 靠子串匹配必然漏 —— 所以有了这条，白名单只是兼容层。
ENV_EXIT_CODE = 2
#: **环境专属**文案（排在崩溃判据之前）：它们各自都是"依赖/语料不在位"，
#: 而不是检查器崩了 —— 但它们**常常带着 Python 堆栈**（ModuleNotFoundError），
#: 所以必须与"崩溃文案"分开判，否则缺依赖会被误记成"引擎的 bug"。
ENV_FIRST_SIGNS = (
    'ModuleNotFoundError', 'ImportError', 'Cannot find module', 'ERR_MODULE_NOT_FOUND',
)
#: 第十七轮→第十八轮：**第三类状态「检查器故障」**。
#: 契约：1 = 被检内容有问题（判据不成立）｜2 = 环境不满足（要跑而跑不成）
#:      ｜**3 = 检查器自己崩了 —— 这可能是引擎的 bug**。
#: 归属不同这件事很要紧：三类混成一两类，就会把"我的 bug"记到"内容"或"环境"账上。
CRASH_EXIT_CODE = 3
#: ⚠️ **兼容层**：崩了但没有用退出码 3 声明的老脚本，只能靠文案认。
#: **结构化信号（退出码 3）才是方向** —— 这张表是待迁移的债，不是判据本身。
#: 顺序要求：**崩溃文案先于环境文案**判（否则 NameError 会被 ENV_SIGNS 里的
#: ModuleNotFoundError 那类词吞成"环境不足"—— 第十六轮真发生过）。
CRASH_SIGNS = (
    'Traceback (most recent call last)', 'NameError', 'SyntaxError', 'IndentationError',
    'UnboundLocalError', 'AttributeError', 'TypeError', 'KeyError', 'IndexError',
    'ZeroDivisionError', 'RecursionError',
)
#: 判据顺序（**崩溃先于环境**，但"明确的缺模块"仍归环境）：
#:   0 通过 → 3 检查器故障(声明) → 2 环境(声明) →
#:   1 且输出含 Python 真堆栈/崩溃名 → 检查器故障 → 1 且含环境文案 → 环境不足 → 1 其他 → 失败
#: 为什么"含环境文案"排在崩溃判据**之后**：第十六轮实测 `NameError` 被
#: `ENV_SIGNS` 里的 `ModuleNotFoundError` 那类词吞成"环境不足" —— 谁先命中决定了归属。
#: 而 `Cannot find module`（Node 缺依赖）**没有 Python 堆栈头**，所以仍会落到环境一档 ✓。

#: 兼容层：文案信号。刻意写窄：宽了会把真实失败误判成「环境问题」，
#: 那正是本项目最反对的失效模式（用「跳过」掩盖真问题）。
#: 但**只防一个方向的分类器，两个方向都会错**——窄了就把环境问题误判成内容失败
#: （审查方实测：`--all` 在缺依赖时报「检查器可能坏了」，73 项成因全是环境）。
#: 所以：结构化退出码为主，文案为辅，并且**两个方向都要有反例**。
ENV_SIGNS = (
    'Cannot find module',          # node_modules 没装
    'ERR_MODULE_NOT_FOUND',
    '快照里没有',                   # 主站快照不在位
    '找不到讲义站 token',           # 兄弟站点不在位
    '目录不存在',
    '无法准备本地服务',              # smoke.mjs / verify-themes.mjs / verify-actions.mjs / shots.mjs
    '未发现任何领域插件',            # verify-engine.mjs
    '未能从 lab-data.js 取到',       # gen-labs-json.mjs
    '测试崩溃',                     # smoke.mjs / verify-actions.mjs / verify-themes.mjs
)

#: "环境不足"的补齐方式：汇总里必须给出**可执行**的那一步，而不是只说"环境不足"。
FIX_HINTS = {
    'Cannot find module': '装依赖：cd apps/linalg-lab && npm install',
    'ERR_MODULE_NOT_FOUND': '装依赖：cd apps/linalg-lab && npm install',
    '无法准备本地服务': '装依赖（puppeteer-core / 浏览器）：cd apps/linalg-lab && npm install',
    '快照里没有': '挂上主站快照，或跳过该项（它需要 --with-adapter）',
    '找不到讲义站 token': '把兄弟站点放在同级目录，或跳过（它是主题 token 的来源）',
    '目录不存在': '确认工作区路径；该项需要仓库外的夹具',
    '未发现任何领域插件': '装依赖 / 确认 Node 能解析本仓库',
    '未能从 lab-data.js 取到': '确认生成物存在：node tools/gen-labs-json.mjs',
    '测试崩溃': '看该脚本的 stderr；多半是浏览器或依赖缺失',
    '未找到 node': '装 Node（≥20）',
    '超时': '加大超时或换机器；该项可能真的卡住',
    '声明式': '该脚本用退出码 2 声明了环境不足；按它的 stderr 补齐',
}


def fix_hint(reason):
    for key, hint in FIX_HINTS.items():
        if key in reason:
            return hint
    return '按该脚本的 stderr 补齐环境'


def last_meaningful_line(text):
    """取最后一行有意义的话——自检脚本的结论都写在最后。"""
    for line in reversed((text or '').strip().split('\n')):
        line = line.strip()
        if line and not line.startswith('['):
            return line
    return '(无输出)'


#: **分类契约**（第十九轮修 D）：`kind` 只允许这五个值，多一个或少一个即红 ——
#: 这样"忘了接一条分支"（第十八轮根因 A：注释写了、`elif` 没插进去）会被契约抓住。
KINDS = ('pass', 'fail', 'not_selected', 'environment', 'crash')


def classify(returncode, out):
    """（退出码, 输出）→ 分类。**纯函数**：把判定链的形状变成可断言的对象。

    ## 这个自检为什么存在（第十九轮我用一晚换来的一条）
    第十八轮我把聚合器改崩过一次（插了一行引用不存在作用域的 `results`），
    当时**没有任何东西会告诉我"聚合器自己坏了"** —— 那一轮五个反例的退出码 1 全是它造成的 ✗。
    那条洞察原话：**"它在聚合器自己身上、不在子进程里"** ⟹ 缺一半：**子进程声明 + 聚合器自检**。
    下面的 `CLASSIFY_CONTRACT` 就是那一半，且**每条都对应一个反例**（否则契约表会变成"没人验的清单"）：
      ('',3,'crash') ⇔ 反例① 结构化崩溃 ｜ ('NameError: boom\n',1,'crash') ⇔ 反例② 文案层崩溃
      ('',2,'environment') ⇔ 反例③ 环境不足 ｜ ('普通失败输出',1,'fail') ⇔ 反例④ 内容失败
      ('',0,'pass')／('',1,'fail')／('',99,'fail') ⇔ 边界
    顺序（崩溃文案先于环境文案；但"明确的缺依赖"仍归环境）：
      0 → pass ｜ 3 → crash（结构化）｜ 2 → environment（结构化）
      1 且含缺依赖文案 → environment ｜ 1 且含崩溃文案 → crash ｜ 1 其他 → fail
    """
    if returncode == 0:
        return 'pass'
    if returncode == CRASH_EXIT_CODE:
        return 'crash'
    if returncode == ENV_EXIT_CODE:
        return 'environment'
    if returncode == 1:
        if any(sign in out for sign in ENV_FIRST_SIGNS):
            return 'environment'
        if ('Traceback (most recent call last)' in out
                or any(sign in out for sign in CRASH_SIGNS)):
            return 'crash'
        if any(sign in out for sign in ENV_SIGNS):
            return 'environment'
    return 'fail'


CLASSIFY_CONTRACT = (
    ('', 0, 'pass'),
    ('', 3, 'crash'),
    ('NameError: boom\n', 1, 'crash'),
    ('ModuleNotFoundError: xx\n', 1, 'environment'),
    ('', 2, 'environment'),
    ('普通失败输出', 1, 'fail'),
    ('', 1, 'fail'),
    ('', 99, 'fail'),
)


def selfcheck_classify():
    """启动自检（纯函数、零成本）：分类契约必须成立 —— 不成立就拒绝继续分类。

    第十八轮我把聚合器改崩过一次（插了一行引用不存在作用域的 `results`），
    当时**没有任何东西会告诉我"聚合器自己坏了"** —— 那一轮四个反例的退出码 1 全是它造成的。
    """
    bad = []
    for out, rc, want in CLASSIFY_CONTRACT:
        got = classify(rc, out)
        if got != want:
            bad.append('classify(%r, %d) = %r，期望 %r' % (out[:24], rc, got, want))
        if got not in KINDS:
            bad.append('分类出没声明的 kind：%r' % got)
    return (not bad), bad

def main():
    # 第十九轮修 D：**聚合器自检** —— 分类契约不成立就立刻退出（不许静默继续分类）
    _ok_c, _bad_c = selfcheck_classify()
    if not _ok_c:
        print('✗ 聚合器的分类契约不成立 —— 拒绝继续分类（否则会把"我的 bug"记到内容/环境账上）：')
        for b in _bad_c:
            print('   - %s' % b)
        return 3
    argv = set(sys.argv[1:])

    # 只报"一共有多少项检查"，供交付闸门核对材料（申报书/PPT/海报）里的数字是否过期。
    # 不跑任何检查，所以很快。由来：项数从 19 变 20 时材料里有 11 个文件写着旧数字，
    # 全靠人肉同步——"同步漏一处"正是本项目最典型的文档缺陷。
    if '--count' in argv:
        print(len(CHECKS))
        return 0

    # 材料里会写"自检 N 项 / 引擎本体 N 行 / 工具 N 行"——这些数字最容易过期，
    # 所以由引擎自己报出来（口径写在这里，别处不许再各算一套），供交付闸门核对。
    # 口径：引擎本体**不含 fixtures/**（夹具是从别的项目复制来的产物，不是引擎代码）。
    if '--stats' in argv:
        import glob as _glob
        import json as _json
        # 用 paths.py 里已有的常量，别自己再推一遍路径（我第一次就推错了一层，返回 0 行）
        eng = [f for f in _glob.glob(os.path.join(ENGINE, '**', '*.py'), recursive=True)
               + _glob.glob(os.path.join(ENGINE, '**', '*.js'), recursive=True)
               if os.sep + 'fixtures' + os.sep not in f]
        eng_lines = sum(sum(1 for _ in open(f, encoding='utf-8', errors='replace')) for f in eng)
        tools = (_glob.glob(os.path.join(HERE, '*.py')) + _glob.glob(os.path.join(HERE, '*.mjs'))
                 + _glob.glob(os.path.join(HERE, '*.js')))
        tool_lines = sum(sum(1 for _ in open(f, encoding='utf-8', errors='replace')) for f in tools)
        print(_json.dumps({'checks': len(CHECKS), 'engine_lines': eng_lines,
                           'tool_lines': tool_lines, 'tool_scripts': len(tools)}, ensure_ascii=False))
        return 0
    want_browser = bool(argv & {'--with-browser', '--all'})
    want_adapter = bool(argv & {'--with-adapter', '--all'})

    print('=== 一键复现：可验证交互式教学内容引擎 ===')
    print('仓库：%s' % REPO)
    print('')

    # rows 是五元组：(分组, 名称, ok, 说明, kind)
    #   kind: pass / fail / not_selected（我没要求跑）/ environment（要跑了但环境不满足）
    rows = []
    for group, name, cmd, need in CHECKS:
        if need == 'browser' and not want_browser:
            rows.append((group, name, None, '未选择（需 --with-browser）', 'not_selected'))
            continue
        if need == 'env-fixtures' and not (want_browser and want_adapter):
            rows.append((group, name, None, '未选择（需 --with-browser 且 --with-adapter）', 'not_selected'))
            continue
        if need == 'adapter' and not want_adapter:
            rows.append((group, name, None, '未选择（需 --with-adapter）', 'not_selected'))
            continue
        if cmd[0] == 'node' and not _has('node'):
            rows.append((group, name, None, '环境不足：未找到 node', 'environment'))
            continue
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=SITE, timeout=1800)
        except subprocess.TimeoutExpired:
            rows.append((group, name, None, '环境不足：超时（>1800s）', 'environment'))
            continue
        out = (r.stdout or '') + (r.stderr or '')
        if r.returncode == 0:
            rows.append((group, name, True, last_meaningful_line(r.stdout), 'pass'))
        elif r.returncode == ENV_EXIT_CODE:
            # 首选判据：子进程**自己声明**"我因环境原因退出"（结构化，不靠文案）
            rows.append((group, name, None,
                         '环境不足（声明式 · 退出码 2）：' + last_meaningful_line(out), 'environment'))
        elif r.returncode == CRASH_EXIT_CODE:
            # 结构化：子进程**自己声明**"我崩了"（与退出码 2 同一套做法）
            rows.append((group, name, None,
                         '检查器故障（声明式 · 退出码 3）：' + last_meaningful_line(out), 'crash'))
        elif r.returncode == 1 and any(sign in out for sign in ENV_FIRST_SIGNS):
            # 缺依赖/语料：**环境**，不是检查器崩溃（虽然它也带堆栈）
            rows.append((group, name, None,
                         '环境不足（文案判据 · 缺依赖）：' + last_meaningful_line(out), 'environment'))
        elif r.returncode == 1 and ('Traceback (most recent call last)' in out
                                    or any(sign in out for sign in CRASH_SIGNS)):
            # 兼容层：**崩溃文案必须先于环境文案判**
            rows.append((group, name, None,
                         '检查器故障（文案判据）：' + last_meaningful_line(out), 'crash'))
        elif any(sign in out for sign in ENV_SIGNS) and r.returncode == 1:
            # 兼容层：靠文案认环境问题。两个方向都有反例守着（见文件头 docstring）
            rows.append((group, name, None, '环境不足（文案判据）：' + last_meaningful_line(out), 'environment'))
        else:
            rows.append((group, name, False, last_meaningful_line(out), 'fail'))

    width = max(len(n) for _, n, _, _, _ in rows) + 2
    cur = None
    for group, name, ok, detail, kind in rows:
        if group != cur:
            print('── %s' % group)
            cur = group
        mark = {'pass': '✓', 'fail': '✗', 'not_selected': '·', 'environment': '–',
              'crash': '⁉'}[kind]
        print('  %s %s%s' % (mark, name.ljust(width), detail))

    # D-2：**兼容层（文案判据）命中数必须出现在汇总里**——它是待迁移的债务：
    # 说明结构化信号（退出码 2）没被走到，而"靠 Node.js vX.Y.Z 这种串认环境"是不稳定的。
    compat_hits = [(g, n) for g, n, ok, d, k in rows if k == 'environment' and '文案判据' in d]
    # 第九轮 §1 要求 2：**「本次未比较 / 未独立验证」必须出现在汇总里**。
    # 判据：子进程按约定打印 `NOT-COMPARED: <原因>`（机器可读的一行协议，由我们自己的脚本输出），
    # 聚合层据此计数——它不是"文案猜环境"，而是一条**声明式协议行**（写在 check-figure-sync.py 的 docstring 里）。
    not_compared = [(g, n) for g, n, ok, d, k in rows if 'NOT-COMPARED:' in (d or '')]
    hard_fail = [(g, n, d) for g, n, ok, d, k in rows if k == 'fail']
    crash_bad = [(g, n, d) for g, n, ok, d, k in rows if k == 'crash']
    env_bad = [(g, n, d) for g, n, ok, d, k in rows if k == 'environment']
    unselected = [(g, n, d) for g, n, ok, d, k in rows if k == 'not_selected']
    print('')
    print('  图例：✓ 通过 ｜ ✗ 失败 ｜ · 未选择（我没要求跑）｜ – 环境不足（要跑了跑不成）')
    if not_compared:
        print('  本次未比较 / 未独立验证：%d 项%s（不适用 ≠ 通过：它们这次没有比过任何东西）'
              % (len(not_compared), ''.join(' ｜ ' + n for _, n in not_compared)))
    print('  环境判据来源：声明式（子进程退出码 2）%d 项 ｜ 兼容层（文案匹配）%d 项%s'
          % (len([1 for g, n, ok, d, k in rows if k == 'environment' and '声明式' in d]),
             len(compat_hits),
             '  ← 兼容层命中应尽量为 0，命中即为待迁移债务（D-2）' if compat_hits else ''))

    # 按分组列出"没跑成"的项 + 原因 + 补齐方式。
    # 为什么必须分组：一个总体的"N 项跳过"无法告诉你"哪一个检查在哪一类产物上全报不适用"（E5 的教训）。
    if env_bad:
        print('')
        print('环境不足的项（%d 个）——**它们既不算通过，也不算失败**：' % len(env_bad))
        g = None
        for grp, name, detail in env_bad:
            if grp != g:
                print('  [%s]' % grp)
                g = grp
            print('    – %s' % name)
            print('       原因：%s' % detail)
            print('       补齐：%s' % fix_hint(detail))
    if unselected:
        print('')
        print('未选择的项（%d 个）——本档不含它们，想要就跑加旗标的档：' % len(unselected))
        g = None
        for grp, name, detail in unselected:
            if grp != g:
                print('  [%s]' % grp)
                g = grp
            print('    · %s —— %s' % (name, detail))

    print('')
    if crash_bad:
        print('检查器故障 %d 项 ⁉ —— **这可能是引擎自己的 bug，不是内容的问题**' % len(crash_bad))
        for _, n, _ in crash_bad:
            print('   - %s' % n)
        print('  → 退出码 3：与"1 内容失败""2 环境不足"并列的第三类；该修的是引擎，不是内容')
        return 3
    if hard_fail:
        print('失败 %d 项 ✗' % len(hard_fail))
        for _, n, _ in hard_fail:
            print('   - %s' % n)
        return 1
    if env_bad:
        # 硬规则：存在环境不足项时，**禁止**打印「全部通过」
        print('不可完整判定 ✗  %d 项环境不足（另有 %d 项未选择）'
              % (len(env_bad), len(unselected)))
        print('  → 退出码 2：既不算通过，也不算代码失败。补齐上面列出的环境后重跑。')
        return 2
    if unselected:
        print('本档全部通过 ✓  %d 项已跑、0 失败；另有 %d 项未选择（见上）'
              % (len(rows) - len(unselected), len(unselected)))
        print('  → 退出码 0 表示**本档范围内**没有失败项；要更全的结论就加 --all 再跑一遍。')
        return 0
    print('全部通过 ✓  %d 项已跑、0 跳过' % len(rows))
    return 0


def _has(prog):
    from shutil import which
    return which(prog) is not None


if __name__ == '__main__':
    sys.exit(main())
