# -*- coding: utf-8 -*-
"""
Olivetti 人脸数据集：朴素贝叶斯（PCA+GaussianNB）与 CNN（PyTorch）训练核心。
对比结果写入由 face_algo_status 负责；刷新后台页请只 import face_algo_status，勿 import 本模块（会经 lazy 链加载 torch 风险已隔离到子进程）。
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Optional, Tuple

import face_model_paths as _fp

from travel.face_algo_status import (
    append_worker_log,
    save_compare_run,
    write_cnn_training_progress,
)

# ---------------------------------------------------------------------------
# 朴素贝叶斯
# ---------------------------------------------------------------------------
NB_LIMITS = {
    "pca_n_components": (10, 200),
    "test_size": (0.15, 0.40),
    "random_state": (0, 2_147_483_647),
    "var_smoothing": (1e-12, 1e-1),
}


def _clamp_nb(key: str, v: Any) -> Any:
    lo, hi = NB_LIMITS[key]
    if key == "var_smoothing":
        fv = float(v)
        return max(lo, min(hi, fv))
    iv = int(v)
    return max(lo, min(hi, iv))


def normalize_nb_params(post: dict) -> Tuple[Optional[dict], Optional[str]]:
    try:
        pca = int(post.get("pca_n_components", 150))
        ts = float(post.get("test_size", 0.25))
        rs = int(post.get("random_state", 42))
        vs = float(post.get("var_smoothing", 1e-9))
    except (TypeError, ValueError):
        return None, "参数格式无效，请填写数字。"

    pca = _clamp_nb("pca_n_components", pca)
    ts = max(NB_LIMITS["test_size"][0], min(NB_LIMITS["test_size"][1], ts))
    rs = _clamp_nb("random_state", rs)
    vs = _clamp_nb("var_smoothing", vs)

    return (
        {
            "pca_n_components": pca,
            "test_size": ts,
            "random_state": rs,
            "var_smoothing": vs,
        },
        None,
    )


def run_naive_bayes_training(
    pca_n_components: int = 150,
    test_size: float = 0.25,
    random_state: int = 42,
    var_smoothing: float = 1e-9,
) -> dict:
    params, err = normalize_nb_params(
        {
            "pca_n_components": pca_n_components,
            "test_size": test_size,
            "random_state": random_state,
            "var_smoothing": var_smoothing,
        }
    )
    if err:
        return {"ok": False, "error": err}

    try:
        import joblib
        import numpy as np
        from sklearn.datasets import fetch_olivetti_faces
        from sklearn.decomposition import PCA
        from sklearn.metrics import accuracy_score, f1_score
        from sklearn.model_selection import train_test_split
        from sklearn.naive_bayes import GaussianNB
        from sklearn.pipeline import Pipeline
    except ImportError as e:
        return {"ok": False, "error": "缺少依赖: scikit-learn / joblib / numpy (%s)" % e}

    os.makedirs(_fp.NAIVE_BAYES_MODEL_DIR, exist_ok=True)
    t0 = time.perf_counter()

    try:
        bundle = fetch_olivetti_faces(
            data_home=_fp.SKLEARN_CACHE,
            shuffle=True,
            random_state=params["random_state"],
            download_if_missing=True,
        )
        X, y = bundle.data, bundle.target

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=params["test_size"],
            random_state=params["random_state"],
            stratify=y,
        )
        n_comp = min(
            params["pca_n_components"],
            X_train.shape[0] - 1,
            X_train.shape[1],
        )
        n_comp = max(10, n_comp)

        pipeline = Pipeline(
            steps=[
                ("pca", PCA(n_components=n_comp, whiten=True, random_state=params["random_state"])),
                ("nb", GaussianNB(var_smoothing=params["var_smoothing"])),
            ]
        )
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        acc = float(accuracy_score(y_test, y_pred))
        macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    except Exception as e:
        return {"ok": False, "error": "训练失败: %s" % str(e)[:500]}

    train_sec = round(time.perf_counter() - t0, 2)
    params_used = {
        **params,
        "pca_n_components_effective": n_comp,
    }

    model_path = os.path.join(_fp.NAIVE_BAYES_MODEL_DIR, "pca_gaussian_nb.joblib")
    meta_path = os.path.join(_fp.NAIVE_BAYES_MODEL_DIR, "training_meta.joblib")
    joblib.dump(pipeline, model_path)
    joblib.dump(
        {
            "n_classes": int(len(np.unique(y))),
            "n_features_flat": int(X.shape[1]),
            "image_shape": (64, 64),
            "pca_n_components": int(n_comp),
            "test_accuracy": acc,
            "macro_f1": macro_f1,
            "sklearn_cache": _fp.SKLEARN_CACHE,
            "train_seconds": train_sec,
            "params": params_used,
        },
        meta_path,
    )

    metrics = {
        "test_accuracy": acc,
        "macro_f1": macro_f1,
        "train_seconds": train_sec,
    }
    save_compare_run("naive_bayes", params_used, metrics)

    return {
        "ok": True,
        "params": params_used,
        "metrics": metrics,
        "model_path": model_path,
    }


# ---------------------------------------------------------------------------
# CNN
# ---------------------------------------------------------------------------
CNN_LIMITS = {
    "epochs": (10, 200),
    "batch_size": (8, 128),
    "lr": (1e-5, 0.05),
    "weight_decay": (0.0, 0.05),
    "dropout_fc1": (0.1, 0.85),
    "dropout_fc2": (0.05, 0.7),
    "test_size": (0.15, 0.40),
    "random_state": (0, 2_147_483_647),
}


def _clamp_cnn(key: str, v: float) -> float:
    lo, hi = CNN_LIMITS[key]
    return max(lo, min(hi, float(v)))


def normalize_cnn_params(post: dict) -> Tuple[Optional[dict], Optional[str]]:
    try:
        epochs = int(post.get("epochs", 80))
        batch_size = int(post.get("batch_size", 32))
        lr = float(post.get("lr", 1e-3))
        wd = float(post.get("weight_decay", 1e-4))
        d1 = float(post.get("dropout_fc1", 0.5))
        d2 = float(post.get("dropout_fc2", 0.3))
        ts = float(post.get("test_size", 0.25))
        rs = int(post.get("random_state", 42))
    except (TypeError, ValueError):
        return None, "参数格式无效，请填写数字。"

    epochs = max(CNN_LIMITS["epochs"][0], min(CNN_LIMITS["epochs"][1], epochs))
    batch_size = max(CNN_LIMITS["batch_size"][0], min(CNN_LIMITS["batch_size"][1], batch_size))
    lr = _clamp_cnn("lr", lr)
    wd = _clamp_cnn("weight_decay", wd)
    d1 = _clamp_cnn("dropout_fc1", d1)
    d2 = _clamp_cnn("dropout_fc2", d2)
    ts = max(CNN_LIMITS["test_size"][0], min(CNN_LIMITS["test_size"][1], ts))
    rs = max(CNN_LIMITS["random_state"][0], min(CNN_LIMITS["random_state"][1], rs))

    return (
        {
            "epochs": epochs,
            "batch_size": batch_size,
            "lr": lr,
            "weight_decay": wd,
            "dropout_fc1": d1,
            "dropout_fc2": d2,
            "test_size": ts,
            "random_state": rs,
        },
        None,
    )


def run_cnn_training(
    epochs: int = 80,
    batch_size: int = 32,
    lr: float = 1e-3,
    weight_decay: float = 1e-4,
    dropout_fc1: float = 0.5,
    dropout_fc2: float = 0.3,
    test_size: float = 0.25,
    random_state: int = 42,
) -> dict:
    try:
        import numpy as np
        import torch
        import torch.nn as nn
        import torch.optim as optim
        from sklearn.datasets import fetch_olivetti_faces
        from sklearn.model_selection import train_test_split
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError as e:
        return {"ok": False, "error": "缺少依赖: torch / numpy / scikit-learn (%s)" % e}

    params, err = normalize_cnn_params(
        {
            "epochs": epochs,
            "batch_size": batch_size,
            "lr": lr,
            "weight_decay": weight_decay,
            "dropout_fc1": dropout_fc1,
            "dropout_fc2": dropout_fc2,
            "test_size": test_size,
            "random_state": random_state,
        }
    )
    if err:
        return {"ok": False, "error": err}

    os.makedirs(_fp.CNN_MODEL_DIR, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    class FaceCNN(nn.Module):
        def __init__(self, num_classes: int, dr1: float, dr2: float):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(1, 32, kernel_size=3, padding=1),
                nn.BatchNorm2d(32),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
                nn.Conv2d(32, 64, kernel_size=3, padding=1),
                nn.BatchNorm2d(64),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
                nn.Conv2d(64, 128, kernel_size=3, padding=1),
                nn.BatchNorm2d(128),
                nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
            )
            self.classifier = nn.Sequential(
                nn.Dropout(dr1),
                nn.Linear(128 * 8 * 8, 256),
                nn.ReLU(inplace=True),
                nn.Dropout(dr2),
                nn.Linear(256, num_classes),
            )

        def forward(self, x):
            x = self.features(x)
            x = torch.flatten(x, 1)
            return self.classifier(x)

    t0 = time.perf_counter()
    progress_lines: list = []
    try:
        bundle = fetch_olivetti_faces(
            data_home=_fp.SKLEARN_CACHE,
            shuffle=True,
            random_state=params["random_state"],
            download_if_missing=True,
        )
        images = bundle.images.astype(np.float32)
        y = bundle.target.astype(np.int64)
        n_classes = len(np.unique(y))
        X = images[:, np.newaxis, :, :]
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=params["test_size"], random_state=params["random_state"], stratify=y
        )

        train_ds = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
        test_ds = TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test))
        train_loader = DataLoader(
            train_ds,
            batch_size=params["batch_size"],
            shuffle=True,
            drop_last=False,
            num_workers=0,
        )
        test_loader = DataLoader(test_ds, batch_size=64, shuffle=False, num_workers=0)

        model = FaceCNN(n_classes, params["dropout_fc1"], params["dropout_fc2"]).to(device)
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(
            model.parameters(), lr=params["lr"], weight_decay=params["weight_decay"]
        )

        def evaluate(loader):
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for xb, yb in loader:
                    xb, yb = xb.to(device), yb.to(device)
                    pred = model(xb).argmax(dim=1)
                    correct += (pred == yb).sum().item()
                    total += yb.size(0)
            return correct / max(total, 1)

        def _log(msg: str) -> None:
            print(msg, flush=True)
            append_worker_log(msg)
            progress_lines.append(msg)
            if len(progress_lines) > 100:
                del progress_lines[:-100]

        n_train = len(train_ds)
        n_test = len(test_ds)
        n_batches = len(train_loader)
        _log(
            "CNN 数据: train=%d test=%d | batch_size=%d batches/epoch=%d epochs=%d device=%s"
            % (
                n_train,
                n_test,
                params["batch_size"],
                n_batches,
                params["epochs"],
                device,
            )
        )
        write_cnn_training_progress(
            {
                "phase": "training",
                "epoch": 0,
                "epochs_total": params["epochs"],
                "train_samples": n_train,
                "test_samples": n_test,
                "batches_per_epoch": n_batches,
                "device": str(device),
            },
            log_lines=progress_lines,
        )

        best_acc = 0.0
        for ep in range(1, params["epochs"] + 1):
            model.train()
            epoch_loss = 0.0
            for bi, (xb, yb) in enumerate(train_loader, start=1):
                xb, yb = xb.to(device), yb.to(device)
                optimizer.zero_grad()
                loss = criterion(model(xb), yb)
                loss.backward()
                optimizer.step()
                lv = float(loss.item())
                epoch_loss += lv
                log_this = bi == 1 or bi == n_batches
                if n_batches <= 12:
                    log_this = True
                elif bi % max(1, n_batches // 4) == 0:
                    log_this = True
                if log_this:
                    _log(
                        "epoch %d/%d batch %d/%d loss=%.4f batch_size=%d"
                        % (ep, params["epochs"], bi, n_batches, lv, xb.size(0))
                    )
                    write_cnn_training_progress(
                        {
                            "phase": "training",
                            "epoch": ep,
                            "epochs_total": params["epochs"],
                            "batch": bi,
                            "batches_per_epoch": n_batches,
                            "last_batch_loss": round(lv, 6),
                            "device": str(device),
                        },
                        log_lines=progress_lines,
                    )
            avg_loss = epoch_loss / max(n_batches, 1)
            val_acc = evaluate(test_loader)
            best_acc = max(best_acc, val_acc)
            _log(
                "epoch %d/%d 小结 train_loss_avg=%.4f val_acc=%.4f best_val=%.4f"
                % (ep, params["epochs"], avg_loss, val_acc, best_acc)
            )
            write_cnn_training_progress(
                {
                    "phase": "training",
                    "epoch": ep,
                    "epochs_total": params["epochs"],
                    "train_loss_avg": round(avg_loss, 6),
                    "val_accuracy": round(val_acc, 6),
                    "best_val_accuracy": round(best_acc, 6),
                    "batches_per_epoch": n_batches,
                    "device": str(device),
                },
                log_lines=progress_lines,
            )

        final_acc = float(evaluate(test_loader))
        best_acc = float(best_acc)

        from sklearn.metrics import f1_score as sk_f1

        all_y = []
        all_pred = []
        model.eval()
        with torch.no_grad():
            for xb, yb in test_loader:
                xb = xb.to(device)
                pred = model(xb).argmax(dim=1).cpu().numpy()
                all_pred.extend(pred.tolist())
                all_y.extend(yb.numpy().tolist())
        cnn_macro_f1 = float(sk_f1(all_y, all_pred, average="macro", zero_division=0))
        write_cnn_training_progress(
            {
                "phase": "saving_model",
                "message": "计算指标完成，正在保存 checkpoint…",
                "device": str(device),
            },
            log_lines=progress_lines,
        )
    except Exception as e:
        err = "训练失败: %s" % str(e)[:500]
        try:
            write_cnn_training_progress(
                {"phase": "error", "error": err, "device": str(device)},
                log_lines=progress_lines,
            )
        except Exception:
            pass
        return {"ok": False, "error": err}

    train_sec = round(time.perf_counter() - t0, 2)
    params_used = dict(params)
    params_used["device"] = str(device)

    ckpt_path = os.path.join(_fp.CNN_MODEL_DIR, "face_cnn.pt")
    meta_path = os.path.join(_fp.CNN_MODEL_DIR, "training_meta.json")

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "n_classes": int(n_classes),
            "in_channels": 1,
            "image_size": 64,
            "epochs_trained": params["epochs"],
            "test_accuracy": final_acc,
            "best_val_accuracy": best_acc,
            "macro_f1": cnn_macro_f1,
            "train_seconds": train_sec,
            "params": params_used,
        },
        ckpt_path,
    )

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "framework": "pytorch",
                "dataset": "olivetti_faces",
                "sklearn_cache": _fp.SKLEARN_CACHE,
                "checkpoint": ckpt_path,
                "n_classes": int(n_classes),
                "test_accuracy": final_acc,
                "best_val_accuracy": best_acc,
                "macro_f1": cnn_macro_f1,
                "train_seconds": train_sec,
                "params": params_used,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    metrics = {
        "test_accuracy": final_acc,
        "best_val_accuracy": best_acc,
        "macro_f1": cnn_macro_f1,
        "train_seconds": train_sec,
    }
    save_compare_run("cnn", params_used, metrics)

    write_cnn_training_progress(
        {
            "phase": "done",
            "test_accuracy": round(final_acc, 6),
            "best_val_accuracy": round(best_acc, 6),
            "macro_f1": round(cnn_macro_f1, 6),
            "train_seconds": train_sec,
            "device": str(device),
        },
        log_lines=progress_lines,
    )

    return {
        "ok": True,
        "params": params_used,
        "metrics": metrics,
        "checkpoint": ckpt_path,
    }