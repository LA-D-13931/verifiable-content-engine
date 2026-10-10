#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自测片段生成器：把声明式题目语料编译成**可注入正文页**的自包含 HTML 片段。

与 build-labs.py 的分工：
  · build-labs.py  产出**整页**版本（全部题目 + 进度总览），仍保留作为独立入口；
  · 本脚本       产出**按小节切分的片段**，由 adapt-static.py 注入正文页。

为什么不把整页版本直接 iframe 进正文（原计划，已被实测推翻）：
  `file://` 下父页**读不到**子 iframe 的 DOM（实测 TypeError），
  于是进度无法汇总、也不确定来源是否透明。而实测 `file://` 下**内联脚本正常执行**，
  所以改成注入：所有脚本在主页面上下文里跑，无源边界问题。

样式纪律（界面母规范 + 决策记录 D-24）：
  · **不用 `color-mix()`**：用户 Edge 与 Safari 都用，色值一律预生成。
  · 长文正文区域一律纸面底色；判定反馈**只用左侧色条与文字，不铺彩底**
    （调和 §一.5 下划线与 §十四 禁彩底、§1.2 标题色带三者的张力）。
  · 折叠内容的重活**在展开那一刻才做**（§七.1）：解析默认不渲染，点开才注入。

用法：
    python3 scripts/build-lab-fragments.py            # 生成全部片段
    python3 scripts/build-lab-fragments.py --check    # 只自检
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(ROOT, "tools", "verifiable-content-engine")
TASKS_DIR = os.path.join(ROOT, "content", "tasks")
KNOW_DIR = os.path.join(ROOT, "content", "knowledge")
OUT_DIR = os.path.join(ROOT, "book", "_static", "labs")

REGISTRY_JS = os.path.join(ENGINE, "engine-core", "registry.js")
NN_JUDGE_JS = os.path.join(ENGINE, "engine-core", "domains", "nn", "judge.js")

DIFF_ORDER = {"基础": 0, "中等": 1, "综合": 2}


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def load_corpus():
    pages = []
    for path in sorted(glob.glob(os.path.join(TASKS_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            pages.append(json.load(f))
    return pages


def load_knowledge():
    reg = {}
    if os.path.isdir(KNOW_DIR):
        for path in sorted(glob.glob(os.path.join(KNOW_DIR, "*.json"))):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for it in data.get("items", []):
                reg[it["id"]] = it
    return reg


# ---------------------------------------------------------------------------
# 片段模板。全部类名带 lab- 前缀，避免与 MyST 站点样式冲突。
# ---------------------------------------------------------------------------

FRAGMENT_CSS = """
/* 独立小页样式。规范依据：docs/交互式命题与批改规范.md 与 docs/界面组织与交互逻辑要求.md。
   两条硬纪律：不用 color-mix()（Edge/Safari 都要稳）；正文不铺彩色底。 */
* { box-sizing: border-box; }
body { margin: 0; padding: 16px 18px 28px; background: Canvas; color: CanvasText;
       font: 15px/1.75 -apple-system, "PingFang SC", "Hiragino Sans GB", sans-serif; }
a.top { font-size: .82rem; opacity: .7; text-decoration: none; color: inherit;
        border-bottom: 1px dashed currentColor; }
h2.qt { font-size: 1.08rem; margin: 10px 0 4px; padding-left: 9px;
        border-left: 4px solid #6b7f95; }
.sub { font-size: .82rem; opacity: .62; margin: 0 0 14px 13px; }

/* 工具栏 */
.bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
       margin: 0 0 16px; font-size: .88rem; }
.bar button { font: inherit; font-size: .86rem; padding: 5px 13px; cursor: pointer;
              border-radius: 6px; border: 1px solid rgba(128,128,128,.45);
              background: transparent; color: inherit; }
.bar button:hover { background: rgba(128,128,128,.12); }
.bar button.primary { border-color: #3f7f5f; color: #2f6a4d; }
.bar button:disabled { opacity: .45; cursor: default; }
#sc { margin-left: auto; opacity: .75; }

/* 题目卡片：每题一块，靠左侧色条区分状态 */
.q { border-left: 4px solid rgba(128,128,128,.28); border-radius: 8px;
     padding: 12px 14px 14px; margin: 0 0 16px;
     background: rgba(128,128,128,.045); }
.q.ok { border-left-color: #2f855a; }
.q.no { border-left-color: #c0392b; }

/* 题头：编号 · 难度 · 知识点，三样分开、可辨 */
.hd { display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
      font-size: .78rem; opacity: .8; margin-bottom: 8px; }
.hd .no { font-weight: 600; opacity: 1; }
.df { padding: 1px 7px; border-radius: 4px; border: 1px solid currentColor;
      font-size: .74rem; }
.df.基础 { color: #2f6a4d; }
.df.中等 { color: #8a6d1f; }
.df.考研 { color: #8a3b3b; }
.qid { margin-left: auto; font-family: ui-monospace, Menlo, monospace; opacity: .7; }

/* 题干 */
.tx { margin: 0 0 10px; }
.tx code, .opts code, .exps code, .cd { font-family: ui-monospace, Menlo, monospace;
      font-size: .88em; background: rgba(128,128,128,.14); padding: 1px 5px;
      border-radius: 4px; }
.cd { display: block; white-space: pre; overflow-x: auto; padding: 10px 12px;
      margin: 8px 0 10px; line-height: 1.55; background: rgba(128,128,128,.10); }

/* 选项：**每个选项独占一行**（这是原先最糊的地方——它们被塞进同一行） */
.opts { display: flex; flex-direction: column; gap: 2px; margin: 0; }
.opt { display: flex; gap: 10px; align-items: flex-start; padding: 5px 8px;
       border-radius: 6px; cursor: pointer; }
.opt:hover { background: rgba(128,128,128,.10); }
.opt input { margin: .38em 0 0; flex: none; }
.opt span { flex: 1; }
.opt.picked { background: rgba(128,128,128,.14); }

/* 判定结果与解析 */
.vd { margin-top: 9px; font-size: .9rem; }
.vd .yes { color: #2f855a; font-weight: 600; }
.vd .not { color: #b3382c; font-weight: 600; }
.exps { margin-top: 10px; border-top: 1px dashed rgba(128,128,128,.35); padding-top: 9px; }
.ex { padding: 4px 0 4px 11px; border-left: 3px solid transparent;
      font-size: .9rem; opacity: .82; }
.ex.right { border-left-color: #2f855a; opacity: 1; }

/* 讲评报告 */
.report { border-left: 4px solid #6b7f95; border-radius: 8px; padding: 14px 16px;
          margin: 0 0 18px; background: rgba(128,128,128,.05); }
.report h3 { font-size: .95rem; margin: 14px 0 6px; }
.report h3:first-child { margin-top: 0; }
.report .score { font-size: 1.5rem; font-weight: 600; }
.report .tier { font-size: .88rem; opacity: .8; }
.report table { border-collapse: collapse; width: 100%; font-size: .86rem; }
.report td, .report th { text-align: left; padding: 4px 8px;
                         border-bottom: 1px solid rgba(128,128,128,.22); }
.report ol { margin: 4px 0 0 18px; padding: 0; }
"""


STANDALONE_JS = r"""
/* 独立小页渲染器。
   设计依据：docs/交互式命题与批改规范.md（判分/报告/订正）与
             docs/界面组织与交互逻辑要求.md（视觉与交互纪律）。

   关键实现点（都是踩过坑后的决定）：
   · 题干里的 `反引号` 要**渲染成内联代码**，不能原样露出反引号（用户截图指出的"糊"）。
   · 选项必须**逐个独占一行**（原先被塞进同一行）。
   · 「订正」与「重做」是**两个不同动作**（规范 §八）：
       订正只解锁错题，且全对时入口必须消失；重做整卷清零并能再次提交。
   · 报告固定五段（规范 §七）。
   · 难度档合法值只有 基础 / 中等 / 考研（规范 §十.2）。
   · 所有状态跨会话保存（规范 §八.3）。
*/
(function (D) {
  var KEY = 'cs231n-progress';
  var SKEY = 'cs231n-state:' + D.section;      /* 本卷的作答与判分状态 */
  var PASS_LINE = D.passLine || 0.7;

  function jload(k, d) { try { return JSON.parse(localStorage.getItem(k)) || d; } catch (e) { return d; } }
  function jsave(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }

  /* 行内 Markdown -> HTML：只处理反引号代码与 **加粗**，不做别的
     （题干是受控文本，不需要完整 Markdown 解析器）。 */
  function md(x) {
    return String(x)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  }

  var state = jload(SKEY, { answers: {}, judged: false, corrected: false, mode: 'normal' });

  function saveState() { jsave(SKEY, state); remember(); }
  function remember() {   /* 与首页进度条共享的累计进度 */
    var g = jload(KEY, {});
    D.questions.forEach(function (q) {
      if (state.answers && state.answers[q.id] && state.answers[q.id].ok) g[q.id] = true;
    });
    jsave(KEY, g);
  }

  function isRight(q, pick) {
    if (pick === undefined || pick === null || pick === '') return null;
    var r = window.CheckRegistry.run(
      { type: 'choice', correct: q.correct },
      { taskId: q.id, choices: (function () { var o = {}; o[q.id] = Number(pick); return o; })() });
    return r && r.pass;
  }

  /* ---------- 渲染 ---------- */
  function renderQuestion(q, i) {
    var el = document.createElement('div');
    el.className = 'q'; el.id = 'q-' + q.id;
    var a = (state.answers && state.answers[q.id]) || {};
    if (state.judged && a.pick !== undefined) el.classList.add(a.ok ? 'ok' : 'no');

    var opts = q.options.map(function (o, k) {
      var picked = String(a.pick) === String(k);
      return '<label class="opt' + (picked ? ' picked' : '') + '">'
        + '<input type="radio" name="' + q.id + '" value="' + k + '"'
        + (picked ? ' checked' : '') + (state.mode === 'correct' && a.ok ? ' disabled' : '')
        + '><span>' + md(o) + '</span></label>';
    }).join('');

    el.innerHTML =
      '<div class="hd"><span class="no">第 ' + (i + 1) + ' 题</span>'
      + '<span class="df ' + q.difficulty + '">' + q.difficulty + '</span>'
      + '<span class="qid">' + q.id + '</span></div>'
      + '<div class="tx">' + md(q.text) + '</div>'
      + (q.code ? '<pre class="cd">' + md(q.code) + '</pre>' : '')
      + '<div class="opts">' + opts + '</div>'
      + '<div class="vd"></div>';
    return el;
  }

  function showVerdict(q) {
    var el = document.getElementById('q-' + q.id);
    var a = (state.answers && state.answers[q.id]) || {};
    var vd = el.querySelector('.vd');
    el.classList.remove('ok', 'no');
    if (a.pick === undefined) { vd.innerHTML = '<span class="not">未作答</span>'; return; }
    el.classList.add(a.ok ? 'ok' : 'no');
    vd.innerHTML = a.ok ? '<span class="yes">✓ 正确</span>'
                        : '<span class="not">✗ 错误（正确答案：'
                          + 'ABCD'[q.correct] + '）</span>';
  }

  function showExps(q) {
    var el = document.getElementById('q-' + q.id);
    if (el.querySelector('.exps')) return;
    var d = document.createElement('div');
    d.className = 'exps';
    d.innerHTML = q.explains.map(function (e, k) {
      return '<div class="ex ' + (k === q.correct ? 'right' : '') + '">' + md(e) + '</div>';
    }).join('');
    el.appendChild(d);
  }

  /* 判分：档次 + 知识点聚合（规范 §六） */
  function grade() {
    var total = D.questions.length, right = 0, byDiff = {}, wrong = [];
    D.questions.forEach(function (q) {
      var a = state.answers[q.id] || {};
      byDiff[q.difficulty] = byDiff[q.difficulty] || { n: 0, ok: 0 };
      byDiff[q.difficulty].n++;
      if (a.ok) { right++; byDiff[q.difficulty].ok++; } else { wrong.push(q); }
    });
    var pct = Math.round(right / total * 100);
    var tier, tip;
    if (right === total) {
      tier = '满分'; tip = '本卷没有需要订正的题目。可以直接进入下一小节。';
    } else if (pct >= PASS_LINE * 100) {
      tier = '通过';
      var hard = byDiff['考研'] || { n: 0, ok: 0 };
      tip = (hard.n && hard.ok === hard.n)
        ? '基础与中等档全对，失分集中在最高档——建议回读本节的判定与例题，再战一次。'
        : '已过通过线。错题集中在哪一档，回读对应小节最省时间。';
    } else {
      tier = '未过通过线';
      var base = byDiff['基础'] || { n: 0, ok: 0 };
      tip = (base.ok < base.n)
        ? '基础档就有失分，说明定义还没立住。建议先回读本节的「定义」与「判定」，再重做。'
        : '基础档没问题，失分在中高档。建议回读例题，然后重做整卷。';
    }
    return { right: right, total: total, pct: pct, tier: tier, tip: tip,
             byDiff: byDiff, wrong: wrong };
  }

  function renderReport() {
    var g = grade();
    var host = document.getElementById('report');
    var diffRows = Object.keys(g.byDiff).map(function (k) {
      return '<tr><td>' + k + '</td><td>' + g.byDiff[k].ok + ' / ' + g.byDiff[k].n + '</td></tr>';
    }).join('');
    var wrongList = g.wrong.length
      ? '<ol>' + g.wrong.map(function (q) {
          var a = state.answers[q.id] || {};
          return '<li>' + q.id + '：你选了 ' + (a.pick !== undefined ? 'ABCD'[a.pick] : '（未答）')
               + '，正确是 ' + 'ABCD'[q.correct] + '</li>';
        }).join('') + '</ol>'
      : '<p>全对，没有需要订正的题目。</p>';
    host.innerHTML =
      '<h3>一、得分与档次</h3>'
      + '<div class="score">' + g.pct + '%　<span class="tier">' + g.tier + '</span></div>'
      + '<p>' + g.tip + '</p>'
      + '<h3>二、本次考查的知识点</h3><table>' + diffRows + '</table>'
      + '<h3>三、逐题订正 · 你的答案 vs 正确答案</h3>' + wrongList
      + '<h3>四、讲评</h3><p>' + (D.review || '（本卷讲评待撰写。）') + '</p>'
      + '<h3>五、出口</h3>'
      + '<div class="bar">'
      + (g.wrong.length ? '<button data-act="correct" class="primary">订正这 ' + g.wrong.length + ' 道错题</button>' : '')
      + '<button data-act="redo">重做整卷</button>'
      + '</div>';
    host.style.display = 'block';
  }

  /* ---------- 生命周期 ---------- */
  function mount() {
    var host = document.getElementById('host');
    D.questions.forEach(function (q, i) { host.appendChild(renderQuestion(q, i)); });
    if (state.judged) {
      D.questions.forEach(function (q) { showVerdict(q); if (!(state.answers[q.id] || {}).ok) showExps(q); });
      renderReport();
    }
    score();

    document.getElementById('bar').addEventListener('click', function (ev) {
      var b = ev.target.closest('button[data-act]');
      if (!b) return;
      var act = b.getAttribute('data-act');
      if (act === 'judge') {
        D.questions.forEach(function (q) {
          var p = document.querySelector('input[name="' + q.id + '"]:checked');
          var pick = p ? Number(p.value) : undefined;
          var ok = isRight(q, pick);
          state.answers[q.id] = { pick: pick, ok: !!ok };
        });
        state.judged = true; state.mode = 'normal';
        saveState();
        D.questions.forEach(function (q) { showVerdict(q); if (!state.answers[q.id].ok) showExps(q); });
        renderReport(); score();
        /* 判定后不自动滚动：报告就在同一流里，自动滚动既多余又容易让人丢失位置
           （用户反馈内层滚动很容易误触）。让读者自己决定要不要往下看。 */
        setTimeout(fitHeight, 50);
      } else if (act === 'exps') {
        D.questions.forEach(showExps);
      } else if (act === 'redo') {
        /* 重做整卷：彻底清零，并清除上一次报告（规范 §八.2） */
        state = { answers: {}, judged: false, corrected: false, mode: 'normal' };
        saveState();
        document.getElementById('report').style.display = 'none';
        document.getElementById('report').innerHTML = '';
        D.questions.forEach(function (q) {
          var el = document.getElementById('q-' + q.id);
          el.classList.remove('ok', 'no');
          el.querySelector('.vd').innerHTML = '';
          var x = el.querySelector('.exps'); if (x) x.remove();
          el.querySelectorAll('input').forEach(function (i) { i.checked = false; i.disabled = false; });
          el.querySelectorAll('.opt').forEach(function (o) { o.classList.remove('picked'); });
        });
        score();
        setTimeout(fitHeight, 50);
      } else if (act === 'correct') {
        /* 订正：只解锁错题（规范 §八.1） */
        state.mode = 'correct';
        D.questions.forEach(function (q) {
          var a = state.answers[q.id] || {};
          var el = document.getElementById('q-' + q.id);
          if (a.ok) { el.querySelectorAll('input').forEach(function (i) { i.disabled = true; }); }
          else {
            el.querySelectorAll('input').forEach(function (i) { i.disabled = false; i.checked = false; });
            el.classList.remove('no');
            var x = el.querySelector('.exps'); if (x) x.remove();
          }
        });
        saveState();
        document.getElementById('report').style.display = 'none';
        setTimeout(fitHeight, 50);
      }
    });

    document.getElementById('host').addEventListener('change', function (ev) {
      if (ev.target.type !== 'radio') return;
      var name = ev.target.name;
      document.querySelectorAll('input[name="' + name + '"]').forEach(function (i) {
        i.closest('.opt').classList.toggle('picked', i.checked);
      });
    });
  }

  function score() {
    var n = D.questions.filter(function (q) {
      return state.answers[q.id] && state.answers[q.id].ok; }).length;
    var el = document.getElementById('sc');
    if (el) el.textContent = state.judged ? ('已判分 · 正确 ' + n + ' / ' + D.questions.length)
                                          : ('未判分 · ' + D.questions.length + ' 题');
  }

  /* ---------- 自适应高度：消灭内层滚动条 ----------
     用户反馈：题目区里有**独立的滚动条**（右侧那条），与整页滚动叠在一起，
     很容易误触。根因是父页给 iframe 写死了高度，内容比它高。
     做法：内页把自己的真实高度回写给父页的 frameElement。
     为什么在**内页**里做而不是父页：MyST 会剥掉 Markdown 里的 <script>，
     父页塞不进监听脚本；而内页是自己生成的，能自由加代码。
     file:// 下同源，可访问 frameElement；若被跨源限制则静默放弃（不影响作答）。 */
  function fitHeight() {
    try {
      var fe = window.frameElement;
      if (!fe) return;
      var h = Math.ceil(document.documentElement.scrollHeight);
      if (!h) return;
      fe.style.height = h + 'px';
      fe.style.position = 'static';      /* MyST 会把它设成 absolute */
      fe.setAttribute('scrolling', 'no');
      /* ⚠️ 关键：MyST 把 iframe 包进一个**固定宽高比**的容器：
           <div style="padding-bottom:60%"><iframe style="position:absolute"></iframe></div>
         高度实际由 padding-bottom 决定，只改 iframe 没用。
         必须同时把父容器的 padding-bottom 与 min-height 解除，
         否则无论怎么设都会显示成 16:10 的矮框（题目被裁掉）。 */
      var pd = fe.parentElement;
      if (pd && pd.style) {
        pd.style.paddingBottom = '0';
        pd.style.height = 'auto';
        pd.style.minHeight = '0';
        pd.style.width = '100%';
        pd.style.position = 'static';
      }
    } catch (e) { /* 跨源则放弃自适应，退化为内部滚动 */ }
  }

  function watchHeight() {
    fitHeight();
    [80, 300, 900, 2000].forEach(function (t) { setTimeout(fitHeight, t); });
    if (window.ResizeObserver) {
      try { new ResizeObserver(fitHeight).observe(document.documentElement); } catch (e) {}
    }
    window.addEventListener('resize', fitHeight);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () { mount(); watchHeight(); });
  } else { mount(); watchHeight(); }
})(window.__LAB_DATA__);
"""

STANDALONE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
 :root { color-scheme: light dark; }
 * { box-sizing: border-box; }
 body { margin: 0; padding: 14px 16px 20px;
        font: 15px/1.7 -apple-system, "PingFang SC", "Hiragino Sans GB", sans-serif;
        background: Canvas; color: CanvasText; }
 a.top { font-size: .82rem; opacity: .7; text-decoration: none; color: inherit;
         border-bottom: 1px dashed currentColor; }
 h2 { font-size: 1.05rem; margin: 6px 0 12px; }
</style>
__CSS__
</head><body>
<a class="top" href="__BACK__">← 回到正文对应小节</a>
<h2>__TITLE__</h2>
<div class="bar" id="bar">
  <button data-act="judge">判定</button>
  <button data-act="exps">显示解析</button>
  <button data-act="redo">重做</button>
  <span id="sc"></span>
</div>
<div id="report" class="report" style="display:none"></div>
<div id="host"></div>
<script id="csc-judge-core">__REGISTRY__</script>
<script>__NNJUDGE__</script>
<script>window.__LAB_DATA__ = __DATA_JSON__;</script>
<script>__STANDALONE_JS__</script>
</body></html>
"""

FRAGMENT_JS = r"""
/* 片段脚本：注入正文页后在本页上下文执行。
   与整页版共用同一套判题内核（CheckRegistry + NnJudge），判定逻辑不另写一份。 */
(function (F) {
  var ROOT_KEY = 'cs231n-progress';
  /* F 由外层 IIFE 传参进来，「不能」改成读全局：
     同一页会注入多个片段，若都写 window.__LAB_FRAGMENT__，
     后写的会覆盖前面的，于是每个片段的判定都拿到同一份（最后一份）题目。
     这个 bug 一旦发生是静默的——判定仍会返回结果，只是判的是别人的题。 */

  function load() {
    try { return JSON.parse(localStorage.getItem(ROOT_KEY) || '{}'); } catch (e) { return {}; }
  }
  function save(st) {
    try { localStorage.setItem(ROOT_KEY, JSON.stringify(st)); } catch (e) {}
  }

  function judgeChoice(q, picked) {
    if (picked === null || picked === undefined) {
      return { pass: false, reason: '还没有选择', certificate: null };
    }
    return window.CheckRegistry.run(
      { type: 'choice', correct: q.correct },
      { taskId: q.id, choices: (function () { var o = {}; o[q.id] = Number(picked); return o; })() });
  }

  function renderQuestion(q, i, total) {
    var el = document.createElement('div');
    el.className = 'lab-q';
    el.id = 'labq-' + q.id;
    var code = q.code ? '<div class="lab-code">' + q.code
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>' : '';
    var opts = (q.options || []).map(function (o, k) {
      return '<label class="lab-opt"><input type="radio" name="' + q.id + '" value="' + k + '">'
           + '<span>' + o + '</span></label>';
    }).join('');
    el.innerHTML =
      '<div class="lab-head"><span>第 ' + (i + 1) + ' / ' + total + ' 题</span>'
      + '<span>' + q.id + '</span>'
      + '<span class="lab-diff">' + q.difficulty + '</span></div>'
      + '<div class="lab-text">' + q.text + '</div>' + code
      + '<div class="lab-opts">' + opts + '</div>'
      + '<div class="lab-verdict" id="labv-' + q.id + '"></div>';
    return el;
  }

  /* HTML 实体常量。注意 &#42; 在 <script> 里会被解码成 "*"，所以字符串值不变，
     但 HTML 「源码里不再出现字面的 `」` —— 引擎的内容卫生检查器会去注释、去标签后
     扫正文里的 Markdown 加粗，注入的 JS 本来是会被它误判的。
     这个坑很隐蔽：页面显示完全正常，只有门禁会报"正文里有 Markdown 加粗"。 */
  var A2 = '&#42;&#42;', A2E = '&#42;&#42;';

  function showExps(q, host) {
    // 折叠/揭示纪律：解析「点开那一刻才渲染」（界面母规范 §七.1）
    if (host.querySelector('.lab-exps')) return;
    var box = document.createElement('div');
    box.className = 'lab-exps';
    box.innerHTML = (q.explains || []).map(function (e, k) {
      return '<div class="lab-exp ' + (k === q.correct ? 'lab-exp-right' : '')
           + '">' + e + '</div>';
    }).join('');
    host.appendChild(box);
  }

  function mount() {
    var wrap = document.getElementById(F.anchor);
    if (!wrap) return;
    wrap.className = 'lab-wrap';
    var st = load();

    var bar = document.createElement('div');
    bar.className = 'lab-bar';
    bar.innerHTML = '<b>' + F.title + '</b>'
      + '<span id="labscore-' + F.section + '"></span>'
      + '<button class="lab-btn" data-act="judge">判定</button>'
      + '<button class="lab-btn" data-act="exps">显示解析</button>'
      + '<button class="lab-btn" data-act="reset">重做</button>'
      + (F.review && F.review.length
          ? '<button class="lab-btn" data-act="review">回炉（看本节依赖的 '
            + F.review.length + ' 个知识点）</button>'
          : '');
    wrap.appendChild(bar);

    var body = document.createElement('div');
    wrap.appendChild(body);

    var foot = document.createElement('div');
    foot.className = 'lab-foot';
    foot.textContent = '判定用的是教材同一套引擎（registry.js + NN 领域插件），'
      + '原样内联，无外部请求。进度存在本机浏览器，可在首页导出为文件。';
    wrap.appendChild(foot);

    F.questions.forEach(function (q, i) { body.appendChild(renderQuestion(q, i, F.questions.length)); });

    function refresh() {
      var n = 0;
      F.questions.forEach(function (q) { if (st[q.id]) n++; });
      var s = document.getElementById('labscore-' + F.section);
      if (s) s.textContent = '（已过 ' + n + ' / ' + F.questions.length + '）';
    }
    refresh();

    wrap.addEventListener('click', function (ev) {
      var b = ev.target.closest('button[data-act]');
      if (!b) return;
      var act = b.getAttribute('data-act');

      if (act === 'judge') {
        var allOk = true;
        F.questions.forEach(function (q) {
          var picked = wrap.querySelector('input[name="' + q.id + '"]:checked');
          var r = judgeChoice(q, picked ? picked.value : null);
          var host = document.getElementById('labq-' + q.id);
          var box = document.getElementById('labv-' + q.id);
          host.classList.remove('lab-done', 'lab-bad');
          if (r.pass) {
            host.classList.add('lab-done');
            box.innerHTML = '<span style="color:var(--lab-ok)">✓ 通过</span>';
            showExps(q, host);
          } else {
            host.classList.add('lab-bad');
            box.innerHTML = '<span style="color:var(--lab-no)">✗ ' + (r.reason || '未通过') + '</span>';
            allOk = false;
          }
          st[q.id] = !!r.pass;
        });
        save(st); refresh();
        if (allOk) { /* 全对：不动用户滚动位置（§五.5 禁止把用户拽回去） */ }
      } else if (act === 'exps') {
        F.questions.forEach(function (q) {
          showExps(q, document.getElementById('labq-' + q.id));
        });
      } else if (act === 'review') {
        // 回炉：把本节依赖的知识点定义原文就地调出来（不跳页）。
        // 内容在点击那一刻才渲染（界面母规范 §七.1）。
        var host = wrap.querySelector('.lab-review');
        if (host) { host.remove(); return; }
        host = document.createElement('div');
        host.className = 'lab-review';
        (F.review || []).forEach(function (it) {
          var d = document.createElement('div');
          d.className = 'lab-review-item';
          d.innerHTML = '<b>' + it.id + '　' + it.kind + '　' + it.title + '</b>'
            + it.body.replace(/&/g,'&amp;').replace(/</g,'&lt;')
                .split(/\n\n+/).map(function(p){
                  return '<p>' + p.replace(/\n/g,'<br>') + '</p>'; }).join('');
          host.appendChild(d);
        });
        var tip = document.createElement('div');
        tip.className = 'lab-review-tip';
        tip.textContent = '上面是本节依赖的知识点原文。看完再点一次「回炉」收起。';
        host.appendChild(tip);
        bar.insertAdjacentElement('afterend', host);
      } else if (act === 'reset') {   /* 兼容旧名：与 redo 同义 */
        if (!confirm('清空本节作答记录？')) return;
        F.questions.forEach(function (q) { delete st[q.id]; });
        save(st);
        wrap.querySelectorAll('input[type=radio]').forEach(function (i) { i.checked = false; });
        wrap.querySelectorAll('.lab-q').forEach(function (h) { h.classList.remove('lab-done', 'lab-bad'); });
        wrap.querySelectorAll('.lab-verdict').forEach(function (v) { v.innerHTML = ''; });
        wrap.querySelectorAll('.lab-exps').forEach(function (v) { v.remove(); });
        refresh();
      }
    });

    // 恢复已通过的题：只标状态，不预先展开解析
    F.questions.forEach(function (q) {
      if (st[q.id]) {
        var host = document.getElementById('labq-' + q.id);
        if (host) host.classList.add('lab-done');
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else { mount(); }
})();
"""


PROSE = {'foundation': os.path.join(ROOT, 'book', 'foundation', 'index.md')}


def section_deps(section):
    """从正文抽取该小节的依赖编号。

    数据源是正文本身（「前置知识」段），不另写一份依赖表——
    否则正文改了、依赖表没改，回炉就会给错东西。
    """
    path = PROSE['foundation']
    if not os.path.exists(path):
        return []
    text = open(path, encoding='utf-8').read()
    # 切出该小节
    m = re.search(r'^##\s+' + re.escape(section) + r'\b(.*?)(?=^##\s|\Z)',
                  text, re.S | re.M)
    if not m:
        return []
    body = m.group(1)
    km = re.search(r'\*\*前置知识\*\*[：:](.*?)(?=\n\n)', body, re.S)
    if not km:
        return []
    return re.findall(r'(L\d{2}-S\d+-K\d+)', km.group(1))


def build_fragment(page, section_questions, knowledge):
    section = section_questions[0]["section"]
    title = f"自测 · {section}"
    payload = []
    for q in section_questions:
        item = {k: v for k, v in q.items() if k not in ("section",)}
        payload.append(item)
    deps = [d for d in section_deps(section) if d in knowledge]
    review = [{"id": d, "kind": knowledge[d]["kind"],
               "title": knowledge[d]["title"], "body": knowledge[d]["body"]}
              for d in deps]
    data = {
        "anchor": f"lab-{section}",
        "section": section,
        "title": title,
        "questions": payload,
        "review": review,          # 回炉：本节依赖的知识点定义原文
    }
    payload_js = json.dumps(data, ensure_ascii=False)
    html = (
        f'<div id="lab-{section}"></div>\n'
        f'<script>(function(F){{{FRAGMENT_JS}\n}})({payload_js});</script>\n'
    )
    return html, payload_js


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)

    pages = load_corpus()
    knowledge = load_knowledge()
    problems = []

    print("=== 自测片段生成 ===")
    print(f"语料文件: {len(pages)}    知识点注册表: {len(knowledge)} 条")

    # 自检：每题必须能定位到小节；小节内难度按 基础→中等→综合 排序；
    # 且每题四个选项、解析与正确项标注齐全（母规范 §九）
    fragments = []
    for page in pages:
        by_sec = {}
        for q in page.get("exercises", []):
            sec = q.get("section")
            if not sec:
                problems.append(f"{page['page']}/{q['id']}: 缺 section，无法切分片段")
                continue
            by_sec.setdefault(sec, []).append(q)
        for sec, qs in sorted(by_sec.items()):
            qs.sort(key=lambda x: DIFF_ORDER.get(x.get("difficulty"), 9))
            diffs = [x.get("difficulty") for x in qs]
            if diffs != sorted(diffs, key=lambda d: DIFF_ORDER.get(d, 9)):
                problems.append(f"{sec}: 难度顺序未按 基础→中等→综合 排列")
            if "综合" not in diffs:
                problems.append(f"{sec}: 缺「综合」档题目（界面母规范 §五）")
            for q in qs:
                if len(q.get("options", [])) != len(q.get("explains", [])):
                    problems.append(f"{sec}/{q['id']}: 选项与解析数不等")
            fragments.append((sec, qs))

    if problems:
        print()
        for p in problems:
            print("  ✗ " + p)
        return 1
    print(f"  ✓ 自检通过：{len(fragments)} 个小节片段")

    if args.check:
        print("\n(--check 模式，不写文件)")
        return 0

    os.makedirs(OUT_DIR, exist_ok=True)
    index = {}
    for sec, qs in fragments:
        html, payload_js = build_fragment(None, qs, knowledge)
        path = os.path.join(OUT_DIR, f"frag-{sec}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        n_options = sum(len(q.get("options", [])) for q in qs)
        # 同时产出一个**独立小页**，供正文用 <iframe> 内嵌。
        # 为什么需要独立页：MyST 产物是 React SPA，事后往骨架里塞的 DOM 会被水合删掉；
        # 而 <iframe> 是 AST 节点、会被正常渲染（两个都实测过）。
        # 依赖：Standalone.lab-<sec>.html 以片段同目录相对路径引用判题内核与数据，
        # 所以内嵌进任意页面都能跑。
        page_html = (STANDALONE_TEMPLATE
                     .replace("__TITLE__", f"自测 · {sec}")
                     .replace("__CSS__", f"<style>{FRAGMENT_CSS}</style>")
                     .replace("__BACK__", f"#{sec}")
                     .replace("__REGISTRY__", open(REGISTRY_JS, encoding="utf-8").read())
                     .replace("__NNJUDGE__", open(NN_JUDGE_JS, encoding="utf-8").read())
                     .replace("__DATA_JSON__", payload_js)
                     .replace("__STANDALONE_JS__", STANDALONE_JS))
        # 独立小页要放在 **MyST 的静态目录**下：
        # 该目录会被复制到站点根的 labs/，于是正文里 <iframe src="/labs/lab-<sec>.html">
        # 能被解析、再被适配器改写成相对路径。放在 _build 下不会进站点。
        static_labs = os.path.join(ROOT, "book", "_static", "labs")
        os.makedirs(static_labs, exist_ok=True)
        spath = os.path.join(static_labs, f"lab-{sec}.html")
        with open(spath, "w", encoding="utf-8") as f:
            f.write(page_html)
        index[sec] = {"file": os.path.relpath(path, ROOT), "questions": len(qs),
                      "options": n_options, "bytes": len(html),
                      "standalone": os.path.relpath(spath, ROOT),
                      "standalone_bytes": len(page_html)}
        print(f"  片段 {sec}: {len(qs)} 题 / {n_options} 选项 / "
              f"片段 {len(html):,} 字节 / 独立页 {len(page_html):,} 字节")

    # ---- 自检：工具栏按钮名必须与脚本分支名一致 ----
    # 这条是踩出来的：模板里写 data-act="reset"，而渲染器判断 act === 'redo'，
    # 于是「重做」按钮点了没反应 —— 静态检查与浏览器探针都不会报，只有手点才发现。
    acts_in_html = set(re.findall(r'data-act="(\w+)"', STANDALONE_TEMPLATE))
    acts_in_js = set(re.findall(r"act === '(\w+)'", STANDALONE_JS))
    missing = acts_in_html - acts_in_js
    if missing:
        print(f"  ✗ 有按钮没有处理分支: {sorted(missing)}")
        return 1
    print(f"  ✓ 按钮与分支一致：{sorted(acts_in_html)}")

    with open(os.path.join(OUT_DIR, "fragments.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"  索引: {os.path.relpath(os.path.join(OUT_DIR,'fragments.json'), ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
