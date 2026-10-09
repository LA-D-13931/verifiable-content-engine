#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「引擎可视化」页（产品形态）。

与 独立校验页.html 的区别
=========================
  独立校验页   报告型：拖 JSON → 出一张表。交付给内容作者用。
  本页         产品型：格子视图 + 点开看证据 + 内置样例。**演示用**。

为什么做成生成器而不是直接写 HTML
==================================
本页要复用 独立校验页.html 里的判题核心（buildCtx / judge / analyze，351 行）。
复制粘贴会让「同一份逻辑存在两处」——本项目已经为此吃过亏（两套指纹工具分叉）。
所以生成器**从独立校验页里现取那段逻辑**，保证两边永远一致。

用法：python3 tools/gen-visual.py
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(HERE)
OUT = os.path.join(APP, '引擎可视化.html')
SRC = os.path.join(APP, '独立校验页.html')

#: 判题核心的起止标记（在独立校验页里）
CORE_START = '/* ============================================================\n   一、自动构造'
CORE_END = '/* ============================================================\n   三、渲染报告'


def extract_core():
    s = open(SRC, encoding='utf-8').read()
    i = s.index(CORE_START)
    j = s.index(CORE_END)
    core = s[i:j].rstrip()
    # 自检：必须包含这几个关键函数，否则说明源文件的标记变了
    for fn in ('function buildCtx', 'function judge', 'function analyze'):
        assert fn in core, '抽取的核心逻辑缺少 %s —— 独立校验页的分节标记可能变了' % fn
    # 去掉重复声明：本页外层已经写了 const Mat = window.Mat，
    # 而源文件那段里也有一行 —— 同一作用域重复 const 会让**整段脚本**
    # 抛 SyntaxError（实测：EngineVisual 直接未定义，页面全废）。
    n_dup = core.count('const Mat = window.Mat;')
    if n_dup:
        core = core.replace('const Mat = window.Mat;', '', 1)
        print('  · 已移除 1 处重复的 const Mat 声明（源文件里有 %d 处）' % n_dup)
    n = len(re.findall(r'^function ', core, re.M))
    return core, n


#: 内置样例：(标题, 一句话说明, 内容)
#: 可加 'faithful': True 表示这一例需要「忠实模式」才暴露缺陷。
# ---------------------------------------------------------------
# 设计依据（实测得来的，不是想当然）：
# 校验页会为每个任务构造「最有利的上下文」——动作日志填满、选择题选正确项、
# 矩阵按判据反推。所以在**这个构造下**能稳定失败的，只有两类：
#   ① 判据要求的条件在数学上不可能满足（如 2×2 矩阵要求秩为 5）
#   ② 判据与场景固定属性冲突（如满秩矩阵要求向量在列空间「外」）
# 我第一版样例用了 actions 类型来演示「恒假任务」，结果**显示通过** ——
# 因为动作日志被填满了。这个教训写在这里，免得下次再犯。
def samples():
    return [
        ('① 目标不可达：满秩矩阵要求向量“在外面”',
         '场景里的矩阵是满秩的，它的列空间就是整个平面 —— 任何向量都在里面。'
         '所以这个任务无论怎么拖都不可能完成。',
         {"faithful": True, "labs": [{
             "id": "demo-unreachable",
             "title": "不可达演示",
             "scene": {"matrix": [[1, 0], [0, 1]],
                       "vectors": [{"id": "v", "data": [1, 1]}]},
             "tasks": [{
                 "id": "outside-full-rank",
                 "text": "把 v 拖到矩阵列空间之外",
                 "check": {"type": "on-span", "op": "out", "target": "v"}
             }]
         }]}),

        ('② 判据不可能：2×2 矩阵要求秩为 5',
         '2×2 矩阵的秩最大是 2。作者写了一个永远达不到的条件，'
         '而页面上看不出任何异常。',
         {"labs": [{
             "id": "demo-impossible-rank",
             "title": "不可能的条件",
             "scene": {"matrix": [[1, 1], [1, 1]]},
             "tasks": [{
                 "id": "rank-five",
                 "text": "把矩阵的秩调到 5",
                 "check": {"type": "rank", "op": "eq", "value": 5}
             }]
         }]}),

        ('③ 判据算错：叉积模长要求 99',
         '两列都是单位正交向量，叉积模长恒为 1。要求它等于 99，'
         '说明作者手算错了 —— 这是真实出现过的缺陷类型。',
         {"faithful": True, "labs": [{
             "id": "demo-cross",
             "title": "判据算错演示",
             "scene": {"space": "3d", "matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 1]]},
             "tasks": [{
                 "id": "cross-mag-99",
                 "text": "让两列的叉积模长等于 99",
                 "check": {"type": "cross-mag", "colA": 0, "colB": 1,
                           "op": "eq", "value": 99}
             }]
         }]}),

        ('④ 无人接管：用了没有实现的判题类型',
         '内容里出现了一个判题类型，但引擎和所有领域插件都不认识它 —— '
         '这道题永远不会被判，而页面同样看不出异常。',
         {"labs": [{
             "id": "demo-none",
             "title": "无人接管演示",
             "tasks": [{
                 "id": "unknown-type",
                 "text": "这一关用了一个没人实现的判题类型",
                 "check": {"type": "not-a-real-type", "value": 1}
             }]
         }]}),

        ('⑤ 作者想错：旋转 90° 的矩阵不可能共线',
         '这个任务要求「让 v 与 Av 共线」，但场景里的矩阵是旋转 90° —— '
         '它把任何非零向量都转成垂直方向，两者永远不可能共线。'
         '作者把「共线」理解错了。',
         {"faithful": True, "labs": [{
             "id": "demo-collinear",
             "title": "不可能共线演示",
             "scene": {"matrix": [[0, -1], [1, 0]],
                       "vectors": [{"id": "v", "data": [1, 1]}]},
             "tasks": [{
                 "id": "collinear-90",
                 "text": "让 v 与 Av 共线",
                 "check": {"type": "collinear", "tolDeg": 4}
             }]
         }]}),

        ('⑥ 对照组：全部正常',
         '四道题都能做出来、判得对 —— 用来证明这个工具不是「见谁都报错」。',
         {"labs": [{
             "id": "demo-ok",
             "title": "正常内容",
             "scene": {"matrix": [[1, 0], [0, 1]]},
             "tasks": [
                 {"id": "rank-ok", "check": {"type": "rank", "op": "eq", "value": 2}},
                 {"id": "det-ok", "check": {"type": "det", "op": "eq", "value": 1, "tol": 0.1}},
                 {"id": "choice-ok", "check": {"type": "choice", "correct": 0}},
                 {"id": "actions-ok", "check": {"type": "actions", "all": ["reset"]}}
             ]
         }]}),
    ]


def build():
    core, n_fn = extract_core()
    return HTML.replace('/*__CORE__*/', core).replace('__NFN__', str(n_fn)), n_fn


HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>内容体检 · 可验证的交互式教学内容引擎</title>
<!--
  引擎可视化页（演示形态）
  ------------------------------------------------------------
  设计目标：让「引擎拦住了什么」变成**看得见**的。
  为什么需要它：引擎拦住的错误是「什么都没发生」—— 页面显示、点击反馈、
  提示文本全都正常，只有那个任务的圆圈永远不变绿。评委看不到被拦住的错误，
  只看到一个没出事的页面。所以本页做三件事：

    ① 格子视图：全部任务变成红绿格子，异常的那一格一眼可见
    ② 点开看证据：每一格点开，显示引擎给出的**原因与反证**
    ③ 内置样例：四个按钮，其中三个是**故意做坏**的内容

  判题核心由 tools/gen-visual.py 从 独立校验页.html 现取（__NFN__ 个函数），
  不复制粘贴 —— 避免同一份逻辑存在两处。
-->
<style>
* { box-sizing: border-box; }
body { margin:0; padding:22px 26px 60px; background:#f4f5f7; color:#1c2027; line-height:1.6;
       font-family:"Songti SC","STSong","PingFang SC","Hiragino Sans GB","Microsoft YaHei",serif; }
h1 { font-size:21px; margin:0 0 3px; color:#16202e; }
.sub { font-size:13px; color:#5a6270; margin-bottom:18px; }
.panel { background:#fff; border:1px solid #dfe2e8; border-radius:10px; padding:15px 17px; margin-bottom:15px; }
h2 { font-size:15px; margin:0 0 10px; color:#16202e; }
.verdict { font-size:15px; padding:12px 16px; border-radius:9px; margin-bottom:15px; font-weight:600; }
.v-ok { background:#eef7f2; border-left:5px solid #2f7a5f; color:#1f5c45; }
.v-bad { background:#fdf0f2; border-left:5px solid #a8445a; color:#8a3247; }

/* 统计条 */
.stats { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:15px; }
.stat { flex:1 1 110px; background:#fff; border:1px solid #dfe2e8; border-radius:9px;
        padding:11px 12px; text-align:center; }
.stat .n { font-size:24px; font-weight:700; line-height:1.1; color:#3e5184; }
.stat .l { font-size:11.5px; color:#4b5563; margin-top:3px; }

/* 格子视图 —— 这一页的主角 */
.grid { display:flex; flex-wrap:wrap; gap:4px; margin:4px 0 6px; }
.cell { width:22px; height:22px; border-radius:4px; cursor:pointer; border:1px solid transparent;
        transition:transform .08s, box-shadow .08s; position:relative; }
.cell:hover { transform:scale(1.35); box-shadow:0 2px 8px rgba(0,0,0,.22); z-index:5; }
.cell.ok   { background:#8fd0b0; }
.cell.bad  { background:#e0798f; box-shadow:0 0 0 2px #a8445a inset; }
.cell.sel  { outline:2px solid #16202e; outline-offset:1px; }
.legend { font-size:12.5px; color:#5a6270; display:flex; gap:16px; align-items:center; flex-wrap:wrap; }
.legend i { display:inline-block; width:13px; height:13px; border-radius:3px;
            vertical-align:-2px; margin-right:5px; }
.group { margin-bottom:11px; }
.group .gt { font-size:12.5px; color:#4b5563; margin-bottom:4px; }
.group .gt b { color:#16202e; }

/* 详情 */
#detail { display:none; }
#detail.on { display:block; }
.d-head { display:flex; justify-content:space-between; align-items:baseline; gap:12px; flex-wrap:wrap; }
.d-title { font-size:15px; font-weight:700; color:#16202e; }
.d-kind { font-size:12.5px; padding:2px 9px; border-radius:11px; background:#fdf0f2; color:#8a3247; }
.d-kind.ok { background:#eef7f2; color:#1f5c45; }
table { width:100%; border-collapse:collapse; font-size:13px; margin-top:9px; }
th, td { border:1px solid #e6e8ec; padding:6px 9px; text-align:left; vertical-align:top; }
th { background:#eef0f4; width:110px; }
code { background:#f1f2f4; border:1px solid #e2e4e8; border-radius:3px; padding:0 3px;
       font-family:"SF Mono",Menlo,monospace; font-size:12px; }
pre { background:#f6f7f9; border:1px solid #e2e4e8; border-radius:6px; padding:9px 11px;
      font-family:"SF Mono",Menlo,monospace; font-size:12px; overflow-x:auto; margin:0; }
.btn { font-family:inherit; font-size:13px; padding:7px 13px; border-radius:8px;
       border:1px solid #c8ccd4; background:#fff; cursor:pointer; margin:0 7px 7px 0; text-align:left; }
.btn:hover { border-color:#3e5184; }
.btn.primary { background:#3e5184; border-color:#3e5184; color:#fff; }
.btn.primary:hover { background:#33456f; }
.btn.warn { border-color:#e0cfa8; background:#fffdf6; }
.note { font-size:12.5px; color:#6b7280; }
</style>
</head>
<body>

<h1>内容体检 · 可验证的交互式教学内容引擎</h1>
<div class="sub">把交互式课件的内容交给引擎，它会告诉你：<b>哪一道学习任务做不出来、作者的判题规则哪里不健全</b>。</div>

<div class="panel">
  <h2>先试一个（三个是故意做坏的，一个是正常的）</h2>
  <div id="sampleBtns"></div>
  <div class="note" id="sampleNote">点任意一个按钮即可当场跑。也可以用下面的拖放区放自己的内容 JSON。</div>
</div>

<div class="panel">
  <h2>或者拖入你自己的内容 JSON</h2>
  <div id="drop" style="border:2px dashed #b9c2d4;border-radius:9px;padding:20px;text-align:center;background:#fafbfc;cursor:pointer">
    <b style="color:#3e5184">把 labs.json 拖到这里</b>
    <div class="note" style="margin-top:5px">或点此选择文件</div>
    <input type="file" id="file" accept=".json,application/json" hidden>
  </div>
</div>

<div id="verdict"></div>
<div class="stats" id="stats"></div>

<div class="panel">
  <h2>全部任务（每格 = 一道学习任务，点开看引擎给出的证据）</h2>
  <div class="legend" style="margin-bottom:9px">
    <span><i style="background:#8fd0b0"></i>可达且判得对</span>
    <span><i style="background:#e0798f"></i>有问题（点开看原因）</span>
    <span class="note">鼠标悬停可看是哪一关</span>
  </div>
  <div id="grid"></div>
</div>

<div class="panel" id="detail">
  <div class="d-head">
    <div class="d-title" id="dTitle"></div>
    <div class="d-kind" id="dKind"></div>
  </div>
  <table id="dTable"></table>
</div>

<script src="../../engine-core/mat.js"></script>
<script src="../../engine-core/registry.js"></script>
<script src="../../engine-core/domains/linalg/judge.js"></script>
<script src="../../engine-core/domains/calculus/judge.js"></script>
<script>
(function () {
'use strict';
const Mat = window.Mat;

/* ============================================================
   判题核心 —— 由 tools/gen-visual.py 从 独立校验页.html 现取
   （__NFN__ 个函数；不复制粘贴，避免同一份逻辑存在两处）
   ============================================================ */
/*__CORE__*/

/* ============================================================
   内置样例
   ============================================================ */
const SAMPLES = __SAMPLES__;

/* ============================================================
   渲染：格子视图
   ============================================================ */
let LAST = null;

function render(res, title) {
    const bad = res.rows.filter(r => !r.pass);

    document.getElementById('verdict').innerHTML =
        '<div class="verdict ' + (bad.length ? 'v-bad' : 'v-ok') + '">' +
        (bad.length
            ? '发现 <b>' + bad.length + '</b> 个任务有问题 —— 在「用户已经做到最好」的假设下仍然判不过，'
              + '说明是内容或判据本身的问题，不是用户不会操作。'
            : '全部 <b>' + res.total + '</b> 个任务通过 —— 在「最有利条件下」都能判定通过。') +
        (title ? ' <span class="note">（' + esc(title) + '）</span>' : '') + '</div>';

    document.getElementById('stats').innerHTML =
        stat(res.total, '任务总数') +
        stat(res.total - bad.length, '可达且判得对', '#2f7a5f') +
        stat(bad.length, '有问题', bad.length ? '#a8445a' : '') +
        stat(res.noHandler, '无人接管') +
        stat(res.threw, '抛异常');

    // 按实验分组画格子
    const groups = {};
    res.rows.forEach((r, i) => {
        (groups[r.lab] = groups[r.lab] || []).push({ r: r, i: i });
    });
    let html = '';
    Object.keys(groups).forEach(function (lab) {
        const cells = groups[lab].map(function (g) {
            const cls = g.r.pass ? 'ok' : 'bad';
            return '<div class="cell ' + cls + '" data-i="' + g.i + '" title="' +
                   esc(g.r.lab + ' / ' + g.r.task + '  [' + g.r.type + ']  ' +
                       (g.r.pass ? '通过' : g.r.kind)) + '"></div>';
        }).join('');
        html += '<div class="group"><div class="gt"><b>' + esc(lab) + '</b>　' +
                groups[lab].length + ' 个任务</div><div class="grid">' + cells + '</div></div>';
    });
    const g = document.getElementById('grid');
    g.innerHTML = html;
    Array.prototype.forEach.call(g.querySelectorAll('.cell'), function (c) {
        c.onclick = function () { showDetail(res, +c.dataset.i); };
    });

    LAST = res;
    document.getElementById('detail').classList.remove('on');
}

function stat(v, label, color) {
    return '<div class="stat"><div class="n"' + (color ? ' style="color:' + color + '"' : '') +
           '>' + v + '</div><div class="l">' + label + '</div></div>';
}

/* ============================================================
   渲染：点开一格看证据
   ============================================================ */
function showDetail(res, idx) {
    const r = res.rows[idx];
    if (!r) return;
    Array.prototype.forEach.call(document.querySelectorAll('.cell'), function (c) {
        c.classList.toggle('sel', +c.dataset.i === idx);
    });

    document.getElementById('dTitle').textContent = r.lab + ' / ' + r.task;
    const kind = document.getElementById('dKind');
    kind.textContent = r.pass ? '可达且判得对' : r.kind;
    kind.className = 'd-kind' + (r.pass ? ' ok' : '');

    let rows = '<tr><th>判题类型</th><td><code>' + esc(r.type) + '</code>　' +
               '<span class="note">决定这道题「怎么算过」</span></td></tr>';
    if (r.pass) {
        rows += '<tr><th>引擎结论</th><td style="color:#1f5c45">存在一种操作能让它通过　' +
                '<span class="note">（引擎找到了一个满足判据的状态）</span></td></tr>';
    } else {
        rows += '<tr><th>引擎结论</th><td style="color:#8a3247">' + esc(r.kind) + '</td></tr>';
        rows += '<tr><th>原因</th><td>' + esc(r.reason || '（无）') + '</td></tr>';
        if (r.cert) {
            rows += '<tr><th>判定依据<br><span class="note">证书</span></th><td>' +
                    '<div class="note" style="margin-bottom:5px">引擎不只说「不对」，' +
                    '它给出算出来的依据 —— 这个依据可以被人独立复核。</div>' +
                    '<pre>' + esc(JSON.stringify(r.cert, null, 1)) + '</pre></td></tr>';
        }
    }
    document.getElementById('dTable').innerHTML = rows;
    document.getElementById('detail').classList.add('on');
    const d = document.getElementById('detail');
    if (d.scrollIntoView) d.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

/* ============================================================
   入口
   ============================================================ */
/* 两种模式，**默认用最有利模式**：
     · 最有利（默认）—— 真实内容在这里应当全绿，适合「打开看一眼」的印象
     · 忠实（按样例单独开）—— 只为暴露「场景与判据冲突」，
       但它会把「用户还没拖」误报成「做不到」（实测 58 关会报 72 个），
       所以**绝不能当默认**，否则一打开满屏红，反而砸招牌。
   这个取舍是实测出来的：我第一版把忠实模式设成默认，真实内容显示了 72 个红格子。 */
const OPTS = {};

function runData(data, title, opts) {
    const labs = data.labs || data;
    if (!Array.isArray(labs)) {
        document.getElementById('verdict').innerHTML =
            '<div class="verdict v-bad">结构不对：找不到 labs 数组。' +
            '期望形如 <code>{ labs: [ { id, tasks: [ … ] } ] }</code>。</div>';
        return;
    }
    render(analyze(data, opts || OPTS), title);
}

function runText(text, title) {
    let data;
    try { data = JSON.parse(text); }
    catch (e) {
        document.getElementById('verdict').innerHTML =
            '<div class="verdict v-bad">这不是合法的 JSON：' + esc(e.message) + '</div>';
        return;
    }
    runData(data, title);
}

// 样例按钮
document.getElementById('sampleBtns').innerHTML = SAMPLES.map(function (s, i) {
    return '<button class="btn ' + (i === SAMPLES.length - 1 ? '' : 'warn') +
           '" data-i="' + i + '">' + esc(s[0]) + '</button>';
}).join('');
Array.prototype.forEach.call(document.querySelectorAll('#sampleBtns .btn'), function (b) {
    b.onclick = function () {
        const s = SAMPLES[+b.dataset.i];
        document.getElementById('sampleNote').innerHTML = '<b>' + esc(s[0]) + '</b>　' + esc(s[1]);
        // 样例自带 faithful 标记：需要暴露「场景与判据冲突」的才用忠实模式
        runData(s[2], s[0], s[2].faithful ? { useScene: true } : {});
    };
});

// 拖放
const drop = document.getElementById('drop'), file = document.getElementById('file');
['dragenter', 'dragover'].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.style.borderColor = '#3e5184'; });
});
['dragleave', 'drop'].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.style.borderColor = '#b9c2d4'; });
});
drop.addEventListener('drop', function (e) {
    const f = e.dataTransfer.files[0];
    if (!f) return;
    const rd = new FileReader();
    rd.onload = function () { runText(rd.result, f.name); };
    rd.readAsText(f);
});
drop.onclick = function () { file.click(); };
file.onchange = function () {
    const f = file.files[0];
    if (!f) return;
    const rd = new FileReader();
    rd.onload = function () { runText(rd.result, f.name); };
    rd.readAsText(f);
};

/* 对外接口（便于自动化验证与将来集成） */
window.EngineVisual = {
    runData: runData,
    runText: runText,
    samples: SAMPLES,
    analyze: analyze,
    analyzeFavorable: function (d) { return analyze(d); },   // 最有利模式（对照）
    buildCtx: buildCtx,
    judge: judge,
    version: '1.0'
};
})();
</script>
</body>
</html>
'''


def main():
    import json
    html, n_fn = build()
    html = html.replace('__SAMPLES__', json.dumps(samples(), ensure_ascii=False, indent=1))
    open(OUT, 'w', encoding='utf-8').write(html)
    print('✓ 已生成 %s' % os.path.basename(OUT))
    print('  复用判题核心函数：%d 个' % n_fn)
    print('  内置样例：%d 个（3 个故意做坏 + 1 个正常对照）' % len(samples()))
    print('  体积：%.0f KB' % (os.path.getsize(OUT) / 1024))


if __name__ == '__main__':
    main()
