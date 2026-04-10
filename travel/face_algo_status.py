# -*- coding: utf-8 -*-
"""
与人脸算法相关的纯文件/子进程逻辑：不 import torch、不在此处做 sklearn 训练。
用于 xadmin 刷新状态（避免加载 PyTorch 导致 Windows 上 runserver 崩溃）。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import face_model_paths as _fp


def append_worker_log(line: str) -> None:
    """CNN 子进程 / 训练循环共用日志（带时间戳）。"""
    os.makedirs(_fp.FACE_MODELS_ROOT, exist_ok=True)
    log_path = os.path.join(_fp.FACE_MODELS_ROOT, "cnn_worker.log")
    ts = datetime.now().isoformat(timespec="seconds")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (ts, line))


def _pid_is_running(pid: int) -> bool:
    if pid is None or int(pid) <= 0:
        return False
    pid = int(pid)
    if sys.platform == "win32":
        try:
            import ctypes

            k = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
            if h:
                k.CloseHandle(h)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _minutes_since_iso(iso_ts: str) -> float:
    if not iso_ts:
        return 99999.0
    try:
        t = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if t.tzinfo:
            return (datetime.now(t.tzinfo) - t).total_seconds() / 60.0
        return (datetime.now() - t).total_seconds() / 60.0
    except Exception:
        return 99999.0


def cnn_training_progress_path() -> str:
    return os.path.join(_fp.FACE_MODELS_ROOT, "cnn_training_progress.json")


def clear_cnn_training_progress() -> None:
    os.makedirs(_fp.FACE_MODELS_ROOT, exist_ok=True)
    with open(cnn_training_progress_path(), "w", encoding="utf-8") as f:
        json.dump(
            {
                "phase": "starting",
                "log_lines": [],
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def write_cnn_training_progress(
    payload: Dict[str, Any],
    log_lines: Optional[List[str]] = None,
) -> None:
    os.makedirs(_fp.FACE_MODELS_ROOT, exist_ok=True)
    data = dict(payload)
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    if log_lines is not None:
        data["log_lines"] = log_lines[-120:]
    with open(cnn_training_progress_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_cnn_training_progress() -> dict:
    p = cnn_training_progress_path()
    if not os.path.isfile(p):
        return {"phase": "idle", "log_lines": [], "updated_at": ""}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"phase": "unknown", "log_lines": [], "updated_at": ""}


def compare_state_path() -> str:
    return os.path.join(_fp.FACE_MODELS_ROOT, "algorithm_compare_state.json")


def load_compare_state() -> dict:
    path = compare_state_path()
    if not os.path.isfile(path):
        return {"naive_bayes": {}, "cnn": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data.setdefault("naive_bayes", {})
        data.setdefault("cnn", {})
        return data
    except Exception:
        return {"naive_bayes": {}, "cnn": {}}


MAX_EXPERIMENT_HISTORY = 400


def experiment_history_path() -> str:
    return os.path.join(_fp.FACE_MODELS_ROOT, "algorithm_experiment_history.json")


def load_experiment_history() -> List[dict]:
    p = experiment_history_path()
    if not os.path.isfile(p):
        return []
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        runs = data.get("runs")
        if isinstance(runs, list):
            return runs
    except Exception:
        pass
    return []


def append_experiment_history(algorithm_key: str, params: dict, metrics: dict) -> None:
    """每次成功保存对比结果时追加一条（含参数与指标）。"""
    os.makedirs(_fp.FACE_MODELS_ROOT, exist_ok=True)
    entry = {
        "algorithm": algorithm_key,
        "params": params,
        "metrics": metrics,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    runs = load_experiment_history()
    runs.insert(0, entry)
    del runs[MAX_EXPERIMENT_HISTORY:]
    with open(experiment_history_path(), "w", encoding="utf-8") as f:
        json.dump({"runs": runs}, f, ensure_ascii=False, indent=2)


def save_compare_run(algorithm_key: str, params: dict, metrics: dict) -> None:
    os.makedirs(_fp.FACE_MODELS_ROOT, exist_ok=True)
    data = load_compare_state()
    saved_at = datetime.now().isoformat(timespec="seconds")
    data[algorithm_key]["last_run"] = {
        "params": params,
        "metrics": metrics,
        "saved_at": saved_at,
    }
    with open(compare_state_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    append_experiment_history(algorithm_key, params, metrics)


def get_compare_state_for_template() -> dict:
    return load_compare_state()


def cnn_job_status_path() -> str:
    return os.path.join(_fp.FACE_MODELS_ROOT, "cnn_job_status.json")


def write_cnn_job_status(
    state: str,
    message: str = "",
    detail: Optional[dict] = None,
) -> None:
    os.makedirs(_fp.FACE_MODELS_ROOT, exist_ok=True)
    rec = {
        "state": state,
        "message": message,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    if detail is not None:
        rec["detail"] = detail
    with open(cnn_job_status_path(), "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)


def read_cnn_job_status() -> dict:
    p = cnn_job_status_path()
    if not os.path.isfile(p):
        return {"state": "idle", "message": "尚无记录", "updated_at": ""}
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"state": "unknown", "message": "无法读取状态文件", "updated_at": ""}


def launch_cnn_training_subprocess(params: dict, base_dir: str) -> Tuple[bool, Optional[str]]:
    """
    在独立 Python 进程中运行 cnn_train_worker.py，避免 PyTorch 与 runserver 同进程导致崩溃。
    base_dir 为项目根目录（settings.BASE_DIR）。
    """
    st = read_cnn_job_status()
    if st.get("state") == "running":
        detail = st.get("detail") or {}
        pid = detail.get("pid")
        alive = _pid_is_running(pid) if pid is not None else False
        if alive:
            return (
                False,
                "训练子进程仍在运行 (pid=%s)。请等待完成或「刷新状态」；勿重复启动。"
                % pid,
            )
        minutes = _minutes_since_iso(st.get("updated_at", ""))
        if pid is None and minutes < 2.0:
            return (
                False,
                "刚写入 running 状态，若持续出现此提示请稍候再试或删除 cnn_job_status.json。",
            )
        append_worker_log(
            "[launch] 自动清除无效 running：pid=%s alive=%s 距今%.1f分钟"
            % (pid, alive, minutes)
        )
        write_cnn_job_status(
            "idle",
            "已自动重置：未发现存活训练进程（或缺少 pid）。可以再次开始训练。",
            detail={"reset": True, "old_pid": pid},
        )

    worker = os.path.join(base_dir, "cnn_train_worker.py")
    if not os.path.isfile(worker):
        return False, "缺少项目根目录下的 cnn_train_worker.py（应与 manage.py 同级）。"

    fm_root = os.path.join(base_dir, "offline", "data", "face_models")
    os.makedirs(fm_root, exist_ok=True)

    fd, params_path = tempfile.mkstemp(prefix="cnn_params_", suffix=".json", dir=fm_root)
    os.close(fd)
    try:
        with open(params_path, "w", encoding="utf-8") as f:
            json.dump(params, f, ensure_ascii=False)
    except OSError as e:
        try:
            os.unlink(params_path)
        except OSError:
            pass
        return False, "写入参数文件失败: %s" % e

    creationflags = 0
    if sys.platform == "win32":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        proc = subprocess.Popen(
            [sys.executable, worker, params_path],
            cwd=base_dir,
            creationflags=creationflags,
        )
    except OSError as e:
        try:
            os.unlink(params_path)
        except OSError:
            pass
        return False, "无法启动子进程: %s" % e

    now = datetime.now().isoformat(timespec="seconds")
    write_cnn_job_status(
        "running",
        "CNN 在独立进程中训练 (pid=%s)。页面下方可看进度；日志: cnn_worker.log"
        % proc.pid,
        detail={"pid": proc.pid, "started_at": now},
    )
    clear_cnn_training_progress()
    append_worker_log("[launch] Popen pid=%s params=%s" % (proc.pid, json.dumps(params)))
    return True, None
