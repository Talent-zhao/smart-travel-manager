# -*- coding: utf-8 -*-
"""
脱离 runserver 的 CNN 训练入口（与 manage.py 同级）。
用法: python cnn_train_worker.py <params_json_path>
"""
from __future__ import annotations

import json
import os
import sys


def main() -> None:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    if len(sys.argv) < 2:
        from travel.face_algo_status import append_worker_log

        append_worker_log("ERROR: missing params json path")
        sys.exit(1)

    params_path = sys.argv[1]
    try:
        with open(params_path, "r", encoding="utf-8") as f:
            params = json.load(f)
    except Exception as e:
        from travel.face_algo_status import append_worker_log

        append_worker_log("ERROR read params: %s" % e)
        sys.exit(1)

    try:
        os.unlink(params_path)
    except OSError:
        pass

    from travel.face_algo_status import append_worker_log, read_cnn_job_status, write_cnn_job_status

    append_worker_log("=== worker start params=%s ===" % json.dumps(params, ensure_ascii=False))

    from travel.face_algo_train import run_cnn_training

    st = read_cnn_job_status()
    merged_detail = dict(st.get("detail") or {})
    merged_detail["worker_phase"] = "run_cnn_training"
    write_cnn_job_status(
        "running",
        "子进程: 正在运行 run_cnn_training（加载 PyTorch）…",
        detail=merged_detail,
    )
    try:
        r = run_cnn_training(**params)
        if r.get("ok"):
            m = r.get("metrics") or {}
            write_cnn_job_status(
                "ok",
                "训练完成。测试准确率 %.4f，耗时 %.1f 秒。"
                % (float(m.get("test_accuracy", 0)), float(m.get("train_seconds", 0))),
                detail={"metrics": m, "params": r.get("params")},
            )
            append_worker_log("OK acc=%.4f" % float(m.get("test_accuracy", 0)))
        else:
            err = (r.get("error") or "失败")[:800]
            write_cnn_job_status("error", err)
            append_worker_log("ERROR: %s" % err)
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        append_worker_log("EXCEPTION: %s\n%s" % (e, tb[-3000:]))
        write_cnn_job_status(
            "error",
            "子进程异常: %s" % str(e)[:500],
            detail={"traceback": tb[-2500:]},
        )

    sys.exit(0)


if __name__ == "__main__":
    main()
