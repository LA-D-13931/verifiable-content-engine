#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读校验：实验数据的 schema 与一致性。

检查项：
  1. 每个实验的必填字段齐全、id 唯一、chapter 存在于 CHAPTERS
  2. scene.matrix 是方阵且与 matrixSize 自洽
  3. 每个 task 的 check.type 在判题器白名单内，且该类型的参数字段齐全
  4. choice 题的 options / explains 数量一致，correct 下标合法
  5. actions 题引用的动作 id 必须在该实验的 toolbar 里真实存在
  6. matrix-col-at / vector-at 的目标维度正确
  7. hints 非空；brief 不超长
  8. 章节至少有 1 个实验

退出码：0 = 全部通过；1 = 有问题。
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
DATA = os.path.join(SITE, 'assets', 'js', 'lab-data.js')

# 矩阵原语统一走 engine/mat.py（唯一权威实现）。
# 本文件原先自带 det2 / rank_of / _intersect_reachable 三份重复实现，
# 与浏览器侧的 assets/js/mat.js 各自演化（容差都不同：这里 1e-9、那边 1e-10）。
# 现已删除重复实现，改为导入；两侧是否算同一个数学由
# engine/mat-vectors.json 的测试向量分别在两侧自检来保证。
sys.path.insert(0, SITE)
from engine.mat import (          # noqa: E402
    EPS as MAT_EPS,
    det as mat_det,
    rank as mat_rank,
    intersect_lines as mat_intersect_lines,
)

# 判题器（engine.js checkTask）支持的类型 → 必填参数
CHECK_SCHEMA = {
    'vector-at': {'required': {'type', 'text', 'check.target', 'check.to'}},
    'av-at': {'required': {'type', 'check.to'}},
    'matrix-col-at': {'required': {'check.col', 'check.to'}},
    'match-matrix': {'required': {'check.matrix'}},
    'det': {'required': {'check.op'}},
    'rank': {'required': {'check.value'}},
    'solve': {'required': {'check.to'}},
    'collinear': {'required': {'check.tolDeg'}},
    'in-basis': {'required': {'check.to'}},
    'vector-angle': {'required': {'check.a', 'check.b', 'check.value'}},
    'intercept': {'required': {'check.tol'}},
    'null-space': {'required': {'check.tol'}},
    'eigen': {'required': {'check.value', 'check.tolDeg'}},
    'in-basis-matrix': {'required': {'check.basis', 'check.matrix'}},
    'dot': {'required': {'check.a', 'check.b', 'check.op'}},
    'cross-mag': {'required': {'check.colA', 'check.colB', 'check.op'}},
    'cross-dir': {'required': {'check.colA', 'check.colB', 'check.dir'}},
    'choice': {'required': {'check.correct', 'options', 'explains'}},
    'actions': {'required': {'check.all'}},
}
WHITELIST = set(CHECK_SCHEMA)

ALLOWED_SCENE_KEYS = {
    'space', 'matrix', 'matrixSize', 'vectors', 'shape', 'lines', 'targetPoint',
    'basis', 'tgrid', 'comboPath', 'metric', 'interact', 'toolbar',
    'spanView', 'nullView', 'basisCoords', 'numLine', 'oneDim', 'dotPair', 'cross'
}
ALLOWED_METRIC = {'det', 'rank', None}
ALLOWED_SPACE = {'2d', '3d'}
ALLOWED_ACTION = {
    'play-transform', 'play-inverse', 'identity', 'preset', 'mul-left',
    'mul-left-inv', 'mul-left-3', 'try-inverse', 'reveal-eigen', 'toggle-space'
}

problems = []
notes = []


def problem(msg):
    problems.append(msg)


COLOR_MAP = {
    'v': '#f6cf72', 'av': '#67e8a5', 'ai': '#fb7185', 'aj': '#c4b5fd',
    'ak': '#8ec5ff', 'grid': '#000', 'tgrid': '#000', 'axis': '#000',
    'prev': '#7b8ea0', 'target': '#f6cf72'
}


def js_to_json(text):
    """把 lab-data.js 里的对象字面量转成 JSON。

    逐字符扫描（不在字符串内的位置才做替换），避免正则误伤中文字符串：
      · 单引号字符串 → 双引号
      · 无引号的对象键 → 加引号
      · 尾随逗号 → 去掉
      · Mat.identity(n) / COLORS.xxx → 字面量
    """
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in '"\'':
            quote = c
            i += 1
            buf = []
            while i < n and text[i] != quote:
                if text[i] == '\\' and i + 1 < n:
                    buf.append(text[i:i + 2])
                    i += 2
                    continue
                buf.append(text[i])
                i += 1
            i += 1
            raw = ''.join(buf)
            if quote == "'":
                raw = raw.replace('"', '\\"')
            out.append('"' + raw + '"')
            continue
        # Mat.identity(n)
        m = re.match(r'Mat\.identity\((\d+)\)', text[i:])
        if m:
            k = int(m.group(1))
            out.append(json.dumps([[1 if a == b else 0 for b in range(k)] for a in range(k)]))
            i += m.end()
            continue
        # COLORS.xxx
        m = re.match(r'COLORS\.(\w+)', text[i:])
        if m:
            out.append(json.dumps(COLOR_MAP.get(m.group(1), '#000')))
            i += m.end()
            continue
        # 无引号键：前面是 { 或 , （跳过空白），后面紧跟 :
        m = re.match(r'([{,]\s*)([A-Za-z_$][\w$]*)\s*:', text[i:])
        if m:
            out.append(m.group(1) + '"' + m.group(2) + '":')
            i += m.end()
            continue
        # 块注释
        if text.startswith('/*', i):
            end = text.find('*/', i + 2)
            i = (end + 2) if end >= 0 else n
            continue
        # 行注释
        if text.startswith('//', i):
            end = text.find('\n', i)
            i = end if end >= 0 else n
            continue
        # 尾随逗号
        if c == ',':
            j = i + 1
            while j < n and text[j] in ' \t\r\n':
                j += 1
            if j < n and text[j] in ']}':
                i += 1
                continue
        out.append(c)
        i += 1
    return re.sub(r'"\s*\+\s*"', '', ''.join(out))


def parse_data():
    """把 lab-data.js 求值成 Python 对象。"""
    src = open(DATA, encoding='utf-8').read()

    def extract(name):
        m = re.search(r'window\.%s\s*=\s*' % name, src)
        if not m:
            raise SystemExit('找不到 window.%s' % name)
        i = src.index('[', m.end())
        depth = 0
        in_str = None
        j = i
        while j < len(src):
            ch = src[j]
            if in_str:
                if ch == '\\':
                    j += 2
                    continue
                if ch == in_str:
                    in_str = None
            elif ch in '"\'':
                in_str = ch
            elif ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:
                    return src[i:j + 1]
            j += 1
        raise SystemExit('%s 数组未闭合' % name)

    return json.loads(js_to_json(extract('CHAPTERS'))), json.loads(js_to_json(extract('LABS')))


# ============================================================
# 教学层校验：任务目标是否可达、辨析题正解是否唯一
# 这一层的目的是拦住「怎么拖都过不了」与「答案不唯一」这两类硬错误。
# ============================================================

def check_reachability(lab, problems, notes):
    """对每个任务穷举检查目标是否落在可达参数空间里。"""
    ctx = '实验 %s' % lab.get('id')
    scene = lab['scene']
    m = scene.get('matrix')
    tol_m = 0.06            # 拖拽吸附精度：0.5 格；用 0.06 作为「必须严格相等」的阈值不合理，
                            # 这里对 match-matrix 用宽松阈值，避免把可达误判成不可达
    for task in lab.get('tasks', []):
        ck = task.get('check', {})
        ct = ck.get('type')
        tctx = '%s 任务 %s' % (ctx, task.get('id'))

        if ct == 'matrix-col-at':
            # 列可以通过拖拽连续调整 ⇒ 目标总是可达；但目标维度要对
            if m and len(ck.get('to', [])) != len(m):
                problems.append('%s 的目标维度与矩阵行数不符' % tctx)
        elif ct == 'match-matrix':
            target = ck.get('matrix')
            if m is None:
                problems.append('%s 要求匹配矩阵，但实验没有矩阵' % tctx)
            elif len(target) != len(m) or any(len(r) != len(m[0]) for r in target):
                problems.append('%s 的目标矩阵形状与当前矩阵不符' % tctx)
        elif ct == 'av-at':
            # Av 可达 ⇔ 目标在列空间里（且要能取到该系数）
            v = next((x for x in scene.get('vectors', []) if x.get('id') == 'v'), None)
            if m is None or v is None:
                problems.append('%s 需要矩阵与 id 为 v 的向量' % tctx)
            elif len(m[0]) != len(v['data']):
                problems.append('%s 的 A 与 v 维度不匹配（%d×%d · %d）'
                                % (tctx, len(m), len(m[0]), len(v['data'])))
            elif not v.get('draggable'):
                problems.append('%s 判定 Av，但 v 不可拖动，用户无法改变结果' % tctx)
            else:
                aug = [row + [ck['to'][i]] for i, row in enumerate(m)]
                if mat_rank(aug) > mat_rank(m):
                    problems.append('%s：目标 %s 不在 A 的列空间里，Av 永远命中不了'
                                    % (tctx, ck.get('to')))
        elif ct == 'det':
            if m is None or len(m) != len(m[0]):
                problems.append('%s 用 det 判定，但当前不是方阵' % tctx)
            elif ck.get('op') == 'eq':
                pass        # 列可连续拖动 ⇒ det 能取到区间内的值，理论上都可达
        elif ct == 'rank':
            if m is None:
                problems.append('%s 用 rank 判定，但没有矩阵' % tctx)
            else:
                r0 = mat_rank(m)
                want = ck.get('value')
                if want > min(len(m), len(m[0])):
                    problems.append('%s 要求 rank=%s，但上限是 %d，不可能达到'
                                    % (tctx, want, min(len(m), len(m[0]))))
                elif not scene.get('interact', {}).get('dragColumns') and r0 != want:
                    # 列不可拖 ⇒ 秩只能通过拖向量改变，而拖向量不改矩阵
                    problems.append('%s 要求 rank=%s，但本实验不允许拖列，秩无法改变（当前 %d）'
                                    % (tctx, want, r0))
        elif ct == 'on-span':
            v = next((x for x in scene.get('vectors', []) if x.get('id') == (ck.get('target') or 'v')), None)
            if v is None or m is None:
                problems.append('%s 需要矩阵和一个可判定向量' % tctx)
            elif not v.get('draggable'):
                problems.append('%s 判定 on-span，但该向量不可拖动' % tctx)
            elif ck.get('op') == 'out' and mat_rank(m) >= min(len(m), len(m[0])):
                problems.append('%s 要求 v 落在列空间外，但列空间已是整个空间（rank 满），做不到' % tctx)
        elif ct == 'solve':
            v = next((x for x in scene.get('vectors', []) if x.get('id') == 'v'), None)
            if m is None or v is None:
                problems.append('%s 需要矩阵与 id 为 v 的向量' % tctx)
            else:
                aug = [row + [ck['to'][i]] for i, row in enumerate(m)]
                if mat_rank(aug) > mat_rank(m):
                    problems.append('%s：b = %s 不在列空间里，Av 永远命中不了'
                                    % (tctx, ck.get('to')))
        elif ct == 'collinear':
            v = next((x for x in scene.get('vectors', []) if x.get('id') == 'v'), None)
            if m is None or len(m) != 2 or v is None:
                problems.append('%s 需要 2×2 矩阵与 id 为 v 的向量' % tctx)
            else:
                tr = m[0][0] + m[1][1]
                disc = tr * tr - 4 * mat_det(m)
                if disc < 0:
                    problems.append('%s：当前矩阵没有实特征方向，共线任务不可能完成' % tctx)
        elif ct == 'vector-at':
            v = next((x for x in scene.get('vectors', []) if x.get('id') == ck.get('target')), None)
            if v is None:
                problems.append('%s 的 target 向量不存在' % tctx)
            elif not v.get('draggable') and v['data'] != ck['to']:
                problems.append('%s 判定向量 %s 到达 %s，但它不可拖动且初始值不符，任务无法完成'
                                % (tctx, ck.get('target'), ck.get('to')))
        elif ct == 'in-basis':
            v = next((x for x in scene.get('vectors', []) if x.get('id') == (ck.get('target') or 'v')), None)
            if m is None or v is None:
                problems.append('%s 需要矩阵与向量' % tctx)
            elif abs(mat_det(m)) < MAT_EPS:
                problems.append('%s：当前矩阵奇异，B⁻¹ 不存在，新基坐标无法定义' % tctx)
            elif not v.get('draggable') and not scene.get('interact', {}).get('dragColumns'):
                problems.append('%s 的 v 与两列都不可动，坐标无法改变' % tctx)
        elif ct == 'vector-angle':
            ids = {x.get('id') for x in scene.get('vectors', [])}
            if ck.get('a') not in ids or ck.get('b') not in ids:
                problems.append('%s 引用的向量不存在' % tctx)
            else:
                va = next(x for x in scene['vectors'] if x['id'] == ck['a'])
                vb = next(x for x in scene['vectors'] if x['id'] == ck['b'])
                if not va.get('draggable') and not vb.get('draggable'):
                    problems.append('%s 两个向量都不可拖动，夹角无法改变' % tctx)
        elif ct == 'dot':
            ids = {x.get('id') for x in scene.get('vectors', [])}
            if ck.get('a') not in ids or ck.get('b') not in ids:
                problems.append('%s 引用的向量不存在' % tctx)
        elif ct in ('cross-mag', 'cross-dir'):
            if m is None or len(m) != 3 or len(m[0]) != 3:
                problems.append('%s 需要 3×3 矩阵' % tctx)
        elif ct == 'actions':
            if not scene.get('toolbar'):
                problems.append('%s 用 actions 判定，但本实验没有工具栏' % tctx)
        elif ct == 'in-basis':
            v = next((x for x in scene.get('vectors', []) if x.get('id') == (ck.get('target') or 'v')), None)
            if m is None or len(m) != 2 or len(m[0]) != 2:
                problems.append('%s 用 in-basis 判定，需要 2×2 矩阵作为新基' % tctx)
            elif abs(mat_det(m)) < MAT_EPS:
                problems.append('%s：当前基不可逆，B⁻¹ 不存在，新基坐标无法定义' % tctx)
            if v is None:
                problems.append('%s 缺少被拖动的向量' % tctx)
            elif not v.get('draggable') and not scene.get('interact', {}).get('dragColumns'):
                problems.append('%s 的 v 与两列都不可动，新基坐标无法改变' % tctx)
        elif ct == 'intercept':
            lines = scene.get('lines', [])
            if len(lines) < 2:
                problems.append('%s 用 intercept 判定，但实验里没有两条以上直线' % tctx)
            else:
                p = mat_intersect_lines(lines)
                if p is None:
                    problems.append('%s：这些直线没有公共交点，拖动 v 永远命中不了' % tctx)
                else:
                    v = next((x for x in scene.get('vectors', []) if x.get('id') == (ck.get('target') or 'v')), None)
                    if v is None:
                        problems.append('%s 缺少被拖动的向量' % tctx)
                    elif not v.get('draggable') and not scene.get('interact', {}).get('dragVectors'):
                        problems.append('%s 的向量不可拖动，无法命中交点' % tctx)
                    elif 'tol' not in ck:
                        notes.append('%s 没写 tol，会用默认 0.15' % tctx)
        elif ct == 'null-space':
            if m is None or len(m) != 2:
                problems.append('%s 用 null-space 判定，需要 2×2 矩阵' % tctx)
            else:
                r = mat_rank(m)
                if r == 2:
                    problems.append('%s：当前矩阵可逆，零空间只有零向量，非零 v 永远不满足' % tctx)
                if r == 1:
                    # 秩 1 时零空间方向是 (-b, a)，检查 target.dir 若给了是否一致
                    a, b = m[0][0], m[0][1]
                    if abs(a) < MAT_EPS and abs(b) < MAT_EPS:
                        a, b = m[1][0], m[1][1]
                    if 'dir' in ck and abs(a) + abs(b) > 1e-9:
                        want = ck['dir']
                        n1 = (a * want[0] + b * want[1])
                        if abs(n1) > 1e-6 * (abs(a) + abs(b)):
                            problems.append('%s：check.dir=%s 不是当前矩阵的零空间方向' % (tctx, want))
            v = next((x for x in scene.get('vectors', []) if x.get('id') == (ck.get('target') or 'v')), None)
            if v is None or not v.get('draggable'):
                problems.append('%s 需要一条可拖动的向量' % tctx)
        elif ct == 'eigen':
            if m is None or len(m) != 2 or len(m[0]) != 2:
                problems.append('%s 用 eigen 判定，需要 2×2 矩阵' % tctx)
            else:
                tr = m[0][0] + m[1][1]
                disc = tr * tr - 4 * mat_det(m)
                if disc < 0:
                    problems.append('%s：当前矩阵没有实特征值，eigen 任务不可能完成' % tctx)
                else:
                    import math as _m
                    sq = _m.sqrt(disc)
                    vals = [(tr + sq) / 2, (tr - sq) / 2]
                    want = ck.get('value')
                    if not any(abs(want - x) < 1e-6 for x in vals):
                        problems.append('%s：目标 λ=%s 不是当前矩阵的特征值（实际为 %s）'
                                        % (tctx, want, [round(x, 4) for x in vals]))
            v = next((x for x in scene.get('vectors', []) if x.get('id') == (ck.get('target') or 'v')), None)
            if v is None or not v.get('draggable'):
                problems.append('%s 需要一条可拖动的向量' % tctx)
        elif ct == 'in-basis-matrix':
            if m is None or len(m) != 2:
                problems.append('%s 用 in-basis-matrix 判定，需要 2×2 矩阵' % tctx)
            elif abs(mat_det(ck['basis'])) < MAT_EPS:
                problems.append('%s：check.basis 不可逆，P⁻¹ 不存在' % tctx)
            elif len(ck.get('matrix', [])) != 2:
                problems.append('%s 的 check.matrix 形状不对' % tctx)


def check_choice_uniqueness(lab, problems):
    """辨析题：正解必须唯一，且 explains 与 options 一一对应。"""
    ctx = '实验 %s' % lab.get('id')
    for task in lab.get('tasks', []):
        if task.get('check', {}).get('type') != 'choice':
            continue
        tctx = '%s 任务 %s' % (ctx, task.get('id'))
        opts = task.get('options', [])
        exps = task.get('explains', [])
        correct = task['check'].get('correct')
        if len(opts) != len(exps):
            problems.append('%s 选项数(%d) 与解释数(%d) 不一致' % (tctx, len(opts), len(exps)))
        if not isinstance(correct, int) or not (0 <= correct < len(opts)):
            problems.append('%s correct 下标越界' % tctx)
            continue
        # 解释文本必须显式标出对错：正解那条以「✓」开头，错误的两条以「✗」开头
        affirmed = [i for i, e in enumerate(exps) if e.strip().startswith('✓')]
        denied = [i for i, e in enumerate(exps) if e.strip().startswith('✗')]
        if affirmed != [correct]:
            problems.append('%s 解释文本里以「✓」开头的有 %s，但正确选项是 %d（应恰好一致）'
                            % (tctx, affirmed, correct))
        if sorted(denied) != [i for i in range(len(exps)) if i != correct]:
            problems.append('%s 解释文本里以「✗」开头的有 %s，应为除 %d 之外的全部'
                            % (tctx, denied, correct))
        # 选项文本必须互不相同（否则用户无法判断该选哪个）
        if len(set(opts)) != len(opts):
            problems.append('%s 存在重复的选项文本' % tctx)
        # 正确选项不能是唯一一个明显的「长选项」——只做提示
        if len(opts) >= 3:
            lens = [len(o) for o in opts]
            if lens[correct] == max(lens) and sorted(lens)[-1] - sorted(lens)[-2] > 12:
                notes.append('%s 正确选项明显比其它选项长，容易被猜中' % tctx)


# ============================================================
# 引擎一致性校验：工具栏动作是否真的会写日志
# ============================================================

# 这些动作的日志名由 tool.log 决定（动态），静态查不出，需要工具栏自带 log 字段
DYNAMIC_LOG_ACTIONS = {'mul-left', 'mul-left-inv', 'mul-left-3'}


def check_action_logging(labs, problems, notes):
    """静态部分：只有一条 —— actions 任务引用的日志名必须真的存在。

    日志名有两种来源：
      · 工具栏的 log 字段（如 undo-b / view-ab）；
      · 动作名本身（如 try-inverse / play-transform）。

    这里只保证「名字有出处」。「动作被点了之后日志是否真的增长」
    属于运行时行为，静态查不可靠（engine 里用的是 logAction(logName) 动态写法），
    所以交给 tools/verify-actions.js 在浏览器里逐个按钮点一遍来验证。
    """
    available = set()
    for lab in labs:
        for tool in lab['scene'].get('toolbar', []):
            available.add(tool.get('log') or tool.get('action'))
    referenced = set()
    for lab in labs:
        for task in lab.get('tasks', []):
            ck = task.get('check', {})
            if ck.get('type') == 'actions':
                referenced.update(ck.get('all', []))
    for name in sorted(referenced - available):
        problems.append('actions 任务引用了日志名 %s，但没有任何工具栏按钮会写入这个名字' % name)


# ============================================================
# 缓存指纹校验：index.html 里的 ?v= 必须与资源内容一致
# ============================================================

def check_theme_tokens(problems, notes):
    """theme-tokens.css / theme-config.js 必须与生成器一致。

    这两个文件是从讲义站的 theme-tokens.css 推导出来的，
    讲义站改了配色、或我改了生成器，都必须重跑 tools/gen-themes.py，
    否则两站的视觉会悄悄漂移。
    """
    gen = os.path.join(SITE, 'tools', 'gen-themes.py')
    if not os.path.exists(gen):
        return
    r = subprocess.run([sys.executable, gen, '--check'],
                       capture_output=True, text=True, cwd=SITE)
    if r.returncode != 0:
        out = (r.stdout or '').strip().split('\n')
        problems.append('主题 token 需要重新生成：%s —— 运行 python3 tools/gen-themes.py'
                        % (out[-1] if out else '未知原因'))


def check_asset_fingerprint(problems, notes):
    """本页用普通 <script src> 加载，URL 不变浏览器就一直用缓存。

    所以 index.html 里的 ?v= 指纹必须跟着资源内容走，
    否则改了 JS 但不更新指纹，用户刷新后跑的还是旧代码——
    6-2 那条任务就是这么反复「修不好」的。
    """
    import hashlib
    files = []
    for sub in ('assets/js', 'assets/css'):
        d = os.path.join(SITE, sub)
        if os.path.isdir(d):
            for fn in sorted(os.listdir(d)):
                if fn.endswith(('.js', '.css')):
                    files.append(os.path.join(d, fn))
    h = hashlib.sha256()
    for f in files:
        h.update(os.path.relpath(f, SITE).encode('utf-8'))
        h.update(open(f, 'rb').read())
    want = h.hexdigest()[:8]

    idx = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
    got = set(re.findall(r'(?:src|href)="assets/[^"]+?\?v=([0-9a-f]+)"', idx))
    n_refs = len(re.findall(r'(?:src|href)="assets/', idx))
    if not got:
        problems.append('index.html 的 %d 处资源引用没有加 ?v= 缓存指纹，'
                        '改了 JS 用户会一直跑旧代码' % n_refs)
    elif got != {want}:
        problems.append('index.html 的资源指纹已过期（%s，应为 %s）——'
                        '运行 python3 tools/加缓存版本.py 修复'
                        % (', '.join(sorted(got)), want))


def main():
    chapters, labs = parse_data()
    ch_ids = {c['id'] for c in chapters}

    if not labs:
        problem('LABS 为空')

    seen_ids = set()
    for lab in labs:
        lid = lab.get('id', '<无 id>')
        ctx = '实验 %s' % lid

        for field in ('id', 'chapter', 'title', 'brief', 'scene', 'tasks'):
            if field not in lab:
                problem('%s 缺少字段 %s' % (ctx, field))
        if not re.fullmatch(r'\d+-\d+', str(lid)):
            problem('%s 的 id 不符合「章-序」格式' % ctx)
        if lid in seen_ids:
            problem('%s 的 id 重复' % ctx)
        seen_ids.add(lid)
        if lab.get('chapter') not in ch_ids:
            problem('%s 的 chapter=%s 不在 CHAPTERS 里' % (ctx, lab.get('chapter')))
        # 章号应与 id 前缀一致
        if str(lid).split('-')[0] != str(lab.get('chapter')):
            problem('%s 的 id 前缀与 chapter 不一致' % ctx)
        if not lab.get('hints'):
            problem('%s 没有 hints' % ctx)
        if len(lab.get('brief', '')) > 260:
            notes.append('%s 的 brief 较长（%d 字），注意右侧栏高度' % (ctx, len(lab['brief'])))

        scene = lab.get('scene', {})
        for k in scene:
            if k not in ALLOWED_SCENE_KEYS:
                problem('%s 的 scene 有未知字段 %s' % (ctx, k))
        space = scene.get('space', '2d')
        if space not in ALLOWED_SPACE:
            problem('%s 的 space=%s 非法' % (ctx, space))
        if scene.get('metric', None) not in ALLOWED_METRIC:
            problem('%s 的 metric=%s 非法' % (ctx, scene.get('metric')))

        m = scene.get('matrix')
        if m is not None:
            rows = len(m)
            cols = len(m[0]) if rows else 0
            if any(len(r) != cols for r in m):
                problem('%s 的 matrix 各行长度不一致' % ctx)
            if scene.get('matrixSize', rows) != rows:
                problem('%s 的 matrixSize 与 matrix 行数不符' % ctx)
            if rows not in (2, 3) or cols not in (2, 3):
                problem('%s 的 matrix 是 %d×%d，本原型只支持 2/3 维' % (ctx, rows, cols))
            if rows == 3 and space != '3d':
                problem('%s 是 3 行矩阵但 space 不是 3d' % ctx)
            if rows != cols:
                notes.append('%s 是 %d×%d 矩形矩阵，面板不显示 det/特征值' % (ctx, rows, cols))
        if scene.get('shape') not in (None, 'square', 'area', 'cube'):
            problem('%s 的 shape=%s 非法' % (ctx, scene.get('shape')))
        if scene.get('shape') == 'cube' and space != '3d':
            problem('%s 用 cube 形状但 space 不是 3d' % ctx)
        if scene.get('tgrid') and m is None:
            notes.append('%s 开了 tgrid 但没有矩阵，变换网格不会出现' % ctx)

        inter = scene.get('interact', {})
        if inter.get('dragColumns') and m is None:
            problem('%s 允许拖列但没有矩阵' % ctx)
        if not inter.get('dragVectors', True) and not inter.get('dragColumns') and lab['tasks']:
            notes.append('%s 没有任何可拖对象，但仍有任务' % ctx)

        # actions 型任务引用的名字 = 工具栏动作写入 actionLog 的名字（engine.js: tool.log || tool.action）
        toolbar_logs = {(t.get('log') or t.get('action')) for t in scene.get('toolbar', [])}
        for tool in scene.get('toolbar', []):
            act = tool.get('action')
            if act not in ALLOWED_ACTION:
                problem('%s 的工具栏动作 %s 未在 engine.js 实现' % (ctx, act))
            if act in ('preset', 'mul-left', 'mul-left-inv', 'mul-left-3') and 'matrix' not in tool:
                problem('%s 的工具栏 %s 缺 matrix' % (ctx, tool.get('id')))

        vec_ids = {v.get('id') for v in scene.get('vectors', [])}
        for v in scene.get('vectors', []):
            if 'data' not in v or not isinstance(v['data'], list):
                problem('%s 的向量 %s 缺 data' % (ctx, v.get('id')))
            elif len(v['data']) not in (2, 3):
                problem('%s 的向量 %s 维度异常' % (ctx, v.get('id')))
            elif 'color' not in v:
                problem('%s 的向量 %s 缺 color' % (ctx, v.get('id')))

        for task in lab.get('tasks', []):
            tid = task.get('id', '<无 id>')
            tctx = '%s 任务 %s' % (ctx, tid)
            if 'id' not in task or 'text' not in task or 'check' not in task:
                problem('%s 缺少 id/text/check' % tctx)
                continue
            ck = task['check']
            ctype = ck.get('type')
            if ctype not in WHITELIST:
                problem('%s 的 check.type=%s 不在判题器白名单内' % (tctx, ctype))
                continue

            if ctype == 'vector-at':
                if ck.get('target') not in vec_ids:
                    problem('%s 的 check.target=%s 不在本实验的 vectors 里' % (tctx, ck.get('target')))
                if len(ck.get('to', [])) not in (2, 3):
                    problem('%s 的 check.to 维度异常' % tctx)
            if ctype == 'matrix-col-at':
                if m is None:
                    problem('%s 用 matrix-col-at 但本实验没有矩阵' % tctx)
                elif ck.get('col') not in (0, 1, 2):
                    problem('%s 的 check.col=%s 非法' % (tctx, ck.get('col')))
                elif m and len(ck.get('to', [])) != len(m):
                    problem('%s 的 check.to 维度与矩阵不符' % tctx)
            if ctype == 'match-matrix':
                if m is None or len(ck.get('matrix', [])) != len(m):
                    problem('%s 的 check.matrix 维度与当前矩阵不符' % tctx)
            if ctype in ('det', 'rank') and m is None:
                problem('%s 用 %s 但本实验没有矩阵' % (tctx, ctype))
            if ctype == 'det' and ck.get('op') not in ('eq', 'lt', 'gt'):
                problem('%s 的 check.op=%s 非法' % (tctx, ck.get('op')))
            if ctype == 'solve':
                if 'v' not in vec_ids:
                    problem('%s 用 solve 但没有 id 为 v 的向量' % tctx)
                if m is None:
                    problem('%s 用 solve 但没有矩阵' % tctx)
            if ctype == 'collinear':
                if 'v' not in vec_ids:
                    problem('%s 用 collinear 但没有 id 为 v 的向量' % tctx)
                if m is None or len(m) != 2:
                    problem('%s 用 collinear 但不是 2×2 矩阵' % tctx)
            if ctype == 'choice':
                opts = task.get('options', [])
                exps = task.get('explains', [])
                if len(opts) < 2:
                    problem('%s 的选项少于 2 个' % tctx)
                if len(exps) != len(opts):
                    problem('%s 的 explains(%d) 与 options(%d) 数量不一致'
                            % (tctx, len(exps), len(opts)))
                if not (0 <= ck.get('correct', -1) < len(opts)):
                    problem('%s 的 correct=%s 下标越界' % (tctx, ck.get('correct')))
            if ctype == 'actions':
                allx = ck.get('all', [])
                if not allx:
                    problem('%s 的 check.all 为空' % tctx)
                for a in allx:
                    if a not in toolbar_logs:
                        problem('%s 引用动作 %s，但工具栏里没有任何按钮会写入这个日志名' % (tctx, a))
                if ck.get('ordered') and len(allx) < 2:
                    notes.append('%s 声明 ordered 但只有一个动作' % tctx)

    # 教学层校验：目标可达性 + 辨析题唯一性
    for lab in labs:
        check_reachability(lab, problems, notes)
        check_choice_uniqueness(lab, problems)
    # 引擎一致性：actions 任务的日志名必须在 engine.js 里真的被写出来
    check_action_logging(labs, problems, notes)
    # 缓存指纹：改了 JS 必须同步更新 index.html 的 ?v=
    check_asset_fingerprint(problems, notes)
    # 主题 token：改过生成器或讲义站配色后必须重新生成
    check_theme_tokens(problems, notes)

    # 还没建设的章节记为提示（分轮建设期间属正常）
    for c in chapters:
        if not any(l.get('chapter') == c['id'] for l in labs):
            notes.append('第 %s 章「%s」尚未建设' % (c['id'], c['title']))

    # 实验数 vs 页面上的硬编码数字
    idx = open(os.path.join(SITE, 'index.html'), encoding='utf-8').read()
    m = re.search(r'实验进度 0/(\d+)', idx)
    if m and int(m.group(1)) != len(labs):
        notes.append('index.html 顶栏初始文案是 0/%s，实际有 %d 个实验（运行时会由 JS 覆盖）'
                     % (m.group(1), len(labs)))
    if 'HTML' not in idx and len(labs) not in (idx.count('11'), 0):
        pass

    print('校验：%d 个章节 · %d 个实验 · %d 个任务'
          % (len(chapters), len(labs), sum(len(l['tasks']) for l in labs)))
    for n in notes:
        print('  · 提示：%s' % n)
    if problems:
        print('\n发现 %d 个问题：' % len(problems))
        for p in problems:
            print('  ✗ %s' % p)
        return 1
    print('\n全部通过 ✓')
    return 0


if __name__ == '__main__':
    sys.exit(main())
