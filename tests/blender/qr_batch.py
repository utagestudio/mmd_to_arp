"""Incremental batch validation (run inside Blender repeatedly until done).

Globals expected before exec():
    REPO         repository root
    LIST_JSON    JSON list of model paths relative to MODELS_DIR
    OUT_JSON     results file (resumed if it exists)
    MODE         'CONVERT' or 'PRESERVE'
    TIME_BUDGET  seconds to spend in this call
    MODELS_DIR   optional, default REPO/_local/mmd
"""
import json
import os
import time

import bpy

for _f in ('mmd_to_arp/detect.py', 'tests/blender/qr_test_helper.py',
           'tests/blender/qr_pose_test.py'):
    exec(open(os.path.join(REPO, _f), encoding='utf-8').read())

_ROOT = globals().get('MODELS_DIR') or os.path.join(REPO, '_local', 'mmd')
_reps = json.load(open(LIST_JSON, encoding='utf-8'))
_results = json.load(open(OUT_JSON, encoding='utf-8')) if os.path.exists(OUT_JSON) else {}
_t0 = time.time()
_new = []
for _r in _reps:
    if _r in _results:
        continue
    if time.time() - _t0 > TIME_BUDGET:
        break
    try:
        _res = validate_model(os.path.join(_ROOT, _r), os.path.join(REPO, 'presets'), mode=MODE)
    except Exception as _e:
        _res = {'error': 'outer ' + repr(_e)[:300]}
    _results[_r] = _res
    _new.append(_r)
    json.dump(_results, open(OUT_JSON, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(_results), '/', len(_reps))
for _k in _new:
    print(_k.split('/')[-1], {a: b for a, b in _results[_k].items() if a not in ('missing', 'model')})
