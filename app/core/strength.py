#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
strength.py —— 密码强度判断（纯逻辑，第 2 步抽取）

基于熵的评分，参考 zxcvbn 算法，返回 0.0 ~ 1.0。
从 GUI 抽出以便独立单元测试，不依赖 tkinter / GUI 状态。
"""
import re
import math


def password_score(pwd):
    """返回密码强度 0.0 ~ 1.0（基于熵计算，参考 zxcvbn 算法）"""
    if not pwd:
        return 0.0

    n = len(pwd)

    # 计算字符集大小
    charset_size = 0
    if re.search(r"[a-z]", pwd):
        charset_size += 26
    if re.search(r"[A-Z]", pwd):
        charset_size += 26
    if re.search(r"\d", pwd):
        charset_size += 10
    if re.search(r"[^a-zA-Z0-9]", pwd):
        charset_size += 33  # 常见特殊字符

    if charset_size == 0:
        return 0.0

    # 计算熵（bits）
    entropy = n * math.log2(charset_size)

    # 惩罚常见模式
    penalty = 0.0

    # 重复字符惩罚
    if len(set(pwd)) == 1:
        penalty += entropy * 0.8

    # 连续字符惩罚（如 abc, 123）
    for i in range(len(pwd) - 2):
        if ord(pwd[i + 1]) == ord(pwd[i]) + 1 and ord(pwd[i + 2]) == ord(pwd[i]) + 2:
            penalty += 10

    # 常见密码模式惩罚
    common_patterns = [
        r"123", r"abc", r"qwerty", r"password", r"admin", r"letmein",
        r"welcome", r"monkey", r"dragon", r"master", r"login", r"princess"
    ]
    pwd_lower = pwd.lower()
    for pattern in common_patterns:
        if pattern in pwd_lower:
            penalty += 20

    # 应用惩罚
    entropy = max(0, entropy - penalty)

    # 将熵映射到 0-1 分数
    # < 28 bits: 非常弱 (0-0.2)
    # 28-35 bits: 弱 (0.2-0.4)
    # 35-60 bits: 中等 (0.4-0.7)
    # 60-80 bits: 强 (0.7-0.9)
    # > 80 bits: 非常强 (0.9-1.0)
    if entropy < 28:
        score = entropy / 28 * 0.2
    elif entropy < 35:
        score = 0.2 + (entropy - 28) / 7 * 0.2
    elif entropy < 60:
        score = 0.4 + (entropy - 35) / 25 * 0.3
    elif entropy < 80:
        score = 0.7 + (entropy - 60) / 20 * 0.2
    else:
        score = 0.9 + min(1, (entropy - 80) / 40) * 0.1

    return min(score, 1.0)