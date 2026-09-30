#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""静态内容校验的入口（统一报告）。

与原脚本的区别（这是「引擎化」的实际价值，不只是换了组织方式）：
  · **统一报告**：九套脚本各有各的输出格式；这里所有检查共用一套结论行
  · **给原因**：原脚本失败时报位置与现象；这里每条检查都给出「为什么」与证书
  · **可扩展**：加一项检查 = 在 checks.py 的 CHECKS 表里加一行

用法：
    python3 verify.py <站点目录>
    python3 verify.py <站点目录> --json     输出机器可读的结果
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checks  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    as_json = '--json' in sys.argv
    allow_outside = '--allow-outside' in sys.argv
    root = os.path.abspath(args[0]) if args else os.getcwd()

    if not os.path.isdir(root):
        print('✗ 目录不存在：%s' % root)
        return 2

    report = checks.run(root, allow_outside=allow_outside)

    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 0 if all(r['pass'] for r in report['results']) else 1

    print('=== 静态内容校验 ===')
    print('目录：%s' % report['root'])
    print('页面：%d' % report['docs'])
    print('')
    width = max(len(r['label']) for r in report['results']) + 2
    for r in report['results']:
        if (r.get('certificate') or {}).get('skipped'):
            mark = '–'          # 跳过：宿主站点没提供这项检查所需的脚本
        else:
            mark = '✓' if r['pass'] else '✗'
        line = '%s %s' % (mark, r['label'].ljust(width))
        cert = r.get('certificate') or {}
        _cert = r.get('certificate') or {}
        detail = (_cert.get('why') if _cert.get('skipped')
                  else (r['reason'] or _summary(r['name'], _cert)))
        print(line + detail)
    bad = [r for r in report['results']
           if not r['pass'] and not (r.get('certificate') or {}).get('skipped')]
    print('')
    if bad:
        print('失败 %d 项 ✗' % len(bad))
        for r in bad:
            print('   - %s：%s' % (r['label'], r['reason']))
        return 1
    _n_skip = sum(1 for r in report['results']
                  if (r.get('certificate') or {}).get('skipped'))
    print('全部通过 ✓ 内容一致性校验无问题'
          + ('（%d 项因宿主站点未提供所需脚本而跳过）' % _n_skip if _n_skip else ''))
    return 0


def _summary(name, cert):
    """通过时也给出统计量，而不是只写「通过」——
    数字能让人看出「检查真的跑了」，而不是空转。"""
    if name == 'tag-balance':
        return '（%d 页，标签全部配平）' % cert.get('files', 0)
    if name == 'internal-links':
        return '（%d 条站内链接全部可达）' % cert.get('checked', 0)
    if name == 'in-page-anchors':
        return '（%d 条页内锚点全部存在）' % cert.get('checked', 0)
    if name == 'content-hygiene':
        return '（%d 页无 Markdown 星号、无 SVG 内数学）' % cert.get('files', 0)
    if name == 'bilingual':
        hard = cert.get('hardChecks') or '—'
        return ('（硬性：%s；另有行文差异 %d 处、节号差异 %d 处供人工确认，不阻断）'
                % (hard, cert.get('inlineSymbolDiff', 0), cert.get('numberMismatch', 0)))
    if name == 'structure':
        c = cert.get('counts') or {}
        if not c:
            return '（委托原脚本执行）'
        return ('（小节 %d · 例题 %d · 测验卷 %d · 测验题 %d · 讲评 %d）'
                % (c['sections'], c['examples'], c['quizPapers'],
                   c['quizQuestions'], c['reviews']))
    return ''


if __name__ == '__main__':
    sys.exit(main())
