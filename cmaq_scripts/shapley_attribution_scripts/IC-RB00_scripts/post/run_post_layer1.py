#!/usr/bin/env python3
"""兼容入口：提取层统一读取配置中的 LAYER，复用 run_post.py 的实现。"""
import sys

from run_post import main


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}. Raw model data are retained unless validation completed.", file=sys.stderr)
        sys.exit(1)
