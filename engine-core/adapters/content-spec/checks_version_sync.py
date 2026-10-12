#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P7 版本同步（第七十轮）—— **机械判据** ✓。

## 先说清"版本号在哪两处声明"（这一步不做，判据就是空的 ✓）
两处**都由 manifest 声明**（不写死在检查里 ✗ —— 本项目 M1 的病就是"两处实现同一件事" ✓）：
    "version_sync": {
      "site":    {"file": "<站点侧文件>",    "field": "<字段/正则名>"},
      "package": {"file": "<安装包侧文件>",  "field": "<字段/正则名>"}
    }
- **站点侧** = 页面/站点数据里那个"版本"（如站点 `assets/course-data.json` 的 `version`）；
- **安装包侧** = 安装包/依赖清单里那个"版本"（如 `package.json` 的 `version`）。

## 判据
- **声明不在** ⇒ `pass=None`「**不适用**：没有声明版本号的两处位置」✓（**不是通过** ✗ —— 查不到 ≠ 一致 ✓）；
- 声明在、**两处取值不等** ⇒ **红** ✓（证书带两个**文件与字段与取值** ✓）；
- 声明在、两处相等 ⇒ 通过 ✓（证书带文件与取值 ✓）。
"""
import json
import os
import re

FIELD = re.compile(r'^\s*"?([A-Za-z_][\w-]*)"?\s*[:=]\s*"?([^",\n}]+)"?')


def _read(path, field):
    """取一处版本：支持 JSON 字段名，也支持"正则名"（形如 /…/ ）✓。"""
    if not os.path.isfile(path):
        return None, '文件不在：%s' % path
    text = open(path, encoding='utf-8').read()
    if field.startswith('/') and field.endswith('/'):
        m = re.search(field.strip('/'), text)
        return (m.group(1) if m and m.groups() else (m.group(0) if m else None)), None
    try:
        d = json.loads(text)
        if isinstance(d, dict) and field in d:
            return d[field], None
    except Exception:
        pass
    for line in text.splitlines():
        m = FIELD.match(line)
        if m and m.group(1) == field:
            return m.group(2).strip(), None
    return None, '字段 %s 在 %s 里找不到' % (field, path)


def run(artifact, source, base):
    decl = (source.get('version_sync') or artifact.get('version_sync'))
    if not decl:
        return {'pass': None,
                'reason': '不适用：**没有声明版本号的两处位置**（未声明 ⇒ 判"不适用"，**不是通过** ✗）',
                'certificate': {'needs': 'declaration', 'where': 'manifest.version_sync'}}
    out = {}
    for side in ('site', 'package'):
        d = decl.get(side) or {}
        v, why = _read(os.path.abspath(os.path.join(base, d.get('file', ''))), str(d.get('field', '')))
        if why:
            return {'pass': None, 'reason': '不适用：%s 侧的声明读不到（%s）' % (side, why),
                    'certificate': {'needs': 'both_sides', 'side': side, 'why': why}}
        out[side] = {'file': d.get('file'), 'field': d.get('field'), 'value': v}
    if out['site']['value'] != out['package']['value']:
        return {'pass': False,
                'reason': '两处版本号**不一致**：站点侧 %s=%s（%s）／安装包侧 %s=%s（%s）'
                          % (out['site']['field'], out['site']['value'], out['site']['file'],
                             out['package']['field'], out['package']['value'], out['package']['file']),
                'certificate': {'verdict': 'fail', 'evidence_type': 'structural', 'detail': out}}
    return {'pass': True, 'reason': '',
            'certificate': {'detail': out, 'equal': out['site']['value']}}
