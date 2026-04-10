# -*- coding: utf-8 -*-
"""
命令行训练（默认超参）：逻辑在 travel.face_algo_train。
与 manage.py 同级执行：python train_face_naive_bayes.py
"""
from __future__ import annotations

from travel.face_algo_train import run_naive_bayes_training

if __name__ == "__main__":
    r = run_naive_bayes_training()
    print(r)
