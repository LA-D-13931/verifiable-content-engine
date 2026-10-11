#!/usr/bin/env bash
# CI 的「判成败 + 自证」逻辑（第五十六轮）——**独立成脚本，所以本机可重放** ✓
#
# 为什么独立成脚本：这段逻辑**不该只能等 CI 才知道对不对** ✗（审计方反例④）。
# 用法（本机重放）：
#   CI_SUMMARY=/tmp/sum.md SUITE_OUT=/tmp/s.out SUITE_ERR=/tmp/s.err CI_RC=2 bash tools/ci-judge.sh
# 退出码：0 = 通过（含"2 = 绿但带标注"）｜ 1 = 失败
set -u
SUMMARY="${CI_SUMMARY:-$GITHUB_STEP_SUMMARY}"
OUT="${SUITE_OUT:-/tmp/suite.out}"
ERR="${SUITE_ERR:-/tmp/suite.err}"
RC="${CI_RC:-$(sed 's/rc=//' /tmp/suite.rc 2>/dev/null || echo '?')}"
# **Summary 同时落一份文件**（第五十七轮）：CI 那边由 upload-artifact 收走 ✓
# —— 这样"原因"对 agent 也是机器可读的（不必靠人看页面 ✓）。
SUM="${SUITE_SUMMARY:-/tmp/suite-summary.md}"
: >"$SUM" 2>/dev/null || true
_sum() { echo "$@" | tee -a "$SUMMARY" >>"$SUM" 2>/dev/null || echo "$@"; }
_out() { tail -40 "$OUT" 2>/dev/null; }
_err() { tail -20 "$ERR" 2>/dev/null; }

{
  echo "## 套件退出码：${RC}" | tee -a "$SUM" 2>/dev/null || true
  echo '### stdout 尾部（40 行）'
  echo '```'
  tail -40 "$OUT" 2>/dev/null || echo '(没有 $OUT)'
  echo '```'
  echo '### stderr 尾部（20 行）'
  echo '```'
  tail -20 "$ERR" 2>/dev/null || echo '(没有 $ERR)'
  echo '```'
} >>"$SUMMARY" 2>/dev/null || true

echo "===== stdout 尾部 ====="; tail -40 "$OUT" 2>/dev/null
echo "===== stderr 尾部 ====="; tail -20 "$ERR" 2>/dev/null

# B-4 守卫：**即使 rc 是 0 或 2**，只要汇总里出现「N 项未选择」且 N>0 ⇒ 判失败 ✓
N_UNSEL=$(grep -oE '另有 [0-9]+ 项未选择|[0-9]+ 项未选择（见上）' "$OUT" 2>/dev/null | grep -oE '[0-9]+' | sort -rn | head -1)
if [ -n "${N_UNSEL:-}" ] && [ "${N_UNSEL:-0}" -gt 0 ]; then
  echo "❌ B-4 守卫：汇总显示 **${N_UNSEL} 项未选择** ⇒ 该跑的没跑 ⇒ 判失败" | tee -a "$SUMMARY"
  exit 1
fi

# N_NOSKIP：退 2 时必须把"本次有 N 条没条件比"打印出来 ✓（不是绿 ✗）
N_ENV=$(grep -oE '本次有 [0-9]+ 条没条件比' "$OUT" 2>/dev/null | grep -oE '[0-9]+' | sort -rn | head -1)
case "${RC}" in
  0) echo "✅ 套件全绿（退出码 0）" | tee -a "$SUMMARY"; exit 0;;
  2) if [ -n "${N_ENV:-}" ]; then
       echo "⚠️ **带标注通过**：本次有 **${N_ENV} 条**没条件比（环境不足，退出码 2）—— **不是绿** ✗" | tee -a "$SUMMARY"
     else
       echo "⚠️ **带标注通过**：退出码 2（环境不足）—— 但**没能从输出里读到"本次有 N 条没条件比"** ✗（如实体现在 Summary 里）" | tee -a "$SUMMARY"
     fi
     exit 0;;
  1) echo "❌ 套件失败：退出码 1 —— 内容/比对不符（"检查器可能坏了"那一类）" | tee -a "$SUMMARY"; exit 1;;
  3) echo "❌ 套件失败：退出码 3 —— 检查器故障（该修的是引擎 ✗）" | tee -a "$SUMMARY"; exit 1;;
  *) echo "❌ 退出码无法识别：${RC}" | tee -a "$SUMMARY"; exit 1;;
esac
