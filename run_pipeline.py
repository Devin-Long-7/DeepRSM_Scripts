"""
RSM 流水线编排脚本

用法:
    # 单个配置
    python run_pipeline.py --configs a_config_d3_202209_M_devin.ini

    # 多个配置并行
    python run_pipeline.py --configs a_config_d3_202209_M_devin.ini a_config_d3_202209_D_devin.ini

    # 预览模式
    python run_pipeline.py --configs a_config_*.ini --dry-run
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

CONDA_BASE = "/home/esil/anaconda3"
WORKING_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(WORKING_DIR, "logs")

ENV_PYTHON = {
    "devin_env": os.path.join(CONDA_BASE, "envs", "devin_env", "bin", "python"),
    "dl": os.path.join(CONDA_BASE, "envs", "dl", "bin", "python"),
}

PIPELINE_STEPS = [
    {"script": "c_data_preprocess.py", "env": "devin_env"},
    {"script": "d_get_equation_item_weight.py", "env": "dl"},
    {"script": "f_rsm_performance.py", "env": "devin_env"},
]

logger = logging.getLogger("run_pipeline")


def parse_args():
    parser = argparse.ArgumentParser(description="RSM 流水线编排脚本")
    parser.add_argument("--configs", nargs="+", required=True, help="一个或多个 INI 配置文件路径")
    parser.add_argument("--max-workers", type=int, default=2, help="最大并行配置数 (默认: 2)")
    parser.add_argument("--dry-run", action="store_true", help="只打印要执行的命令，不实际运行")
    parser.add_argument("--timeout", type=int, default=7200, help="每步超时秒数 (默认: 7200)")
    return parser.parse_args()


def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(LOG_DIR, "pipeline.log"), mode="a"),
        ],
    )


def resolve_config(path):
    """将相对路径解析为绝对路径（基于 WORKING_DIR）"""
    if not os.path.isabs(path):
        path = os.path.join(WORKING_DIR, path)
    return os.path.abspath(path)


def run_step(step, config_path, step_idx, total_steps, config_name, timeout):
    """运行单个流水线步骤，返回 (success, duration, log_file)"""
    script = step["script"]
    python = ENV_PYTHON[step["env"]]
    cmd = [python, os.path.join(WORKING_DIR, script), "--config", config_path]

    log_file = os.path.join(LOG_DIR, f"{config_name}_{script.replace('.py', '')}.log")
    logger.info("[%s] Step %d/%d: %s (%s)", config_name, step_idx, total_steps, script, step["env"])

    start = time.time()
    try:
        with open(log_file, "w") as f:
            result = subprocess.run(
                cmd, cwd=WORKING_DIR, stdout=f, stderr=subprocess.STDOUT,
                text=True, timeout=timeout,
            )
    except subprocess.TimeoutExpired:
        duration = time.time() - start
        logger.error("[%s] Step %d/%d: TIMEOUT after %ds", config_name, step_idx, total_steps, int(duration))
        return False, duration, log_file
    except Exception as e:
        duration = time.time() - start
        logger.error("[%s] Step %d/%d: 异常 %s", config_name, step_idx, total_steps, e)
        return False, duration, log_file

    duration = time.time() - start
    if result.returncode != 0:
        logger.error("[%s] Step %d/%d: FAILED (exit %d, %.0fs)", config_name, step_idx, total_steps, result.returncode, duration)
        # 打印最后几行错误日志
        with open(log_file) as f:
            lines = f.read().splitlines()
            for line in lines[-5:]:
                logger.error("  %s", line)
        return False, duration, log_file

    logger.info("[%s] Step %d/%d: completed (%.0fs)", config_name, step_idx, total_steps, duration)
    return True, duration, log_file


def run_config(config_path, timeout):
    """串行运行一个配置的全部流水线步骤"""
    config_name = os.path.splitext(os.path.basename(config_path))[0]
    logger.info("[%s] 开始流水线", config_name)

    results = []
    total = len(PIPELINE_STEPS)
    for i, step in enumerate(PIPELINE_STEPS, 1):
        success, duration, log_file = run_step(step, config_path, i, total, config_name, timeout)
        results.append({"step": step["script"], "success": success, "duration": duration, "log": log_file})
        if not success:
            # 记录跳过的步骤
            for j in range(i, total):
                skipped = PIPELINE_STEPS[j]["script"]
                results.append({"step": skipped, "success": None, "duration": 0, "log": None})
            break

    passed = sum(1 for r in results if r["success"] is True)
    status = "PASS" if passed == total else "FAIL"
    logger.info("[%s] %s (%d/%d steps)", config_name, status, passed, total)
    return {"config": config_name, "status": status, "results": results}


def print_summary(all_results):
    """打印最终汇总"""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for r in all_results:
        icon = "PASS" if r["status"] == "PASS" else "FAIL"
        completed = [s["step"] for s in r["results"] if s["success"] is True]
        failed = [s["step"] for s in r["results"] if s["success"] is False]
        skipped = [s["step"] for s in r["results"] if s["success"] is None]
        print(f"[{icon}] {r['config']}")
        if completed:
            print(f"     Completed: {', '.join(completed)}")
        if failed:
            print(f"     Failed:    {', '.join(failed)}")
            # 找到失败步骤的日志
            for s in r["results"]:
                if s["success"] is False and s["log"]:
                    print(f"     Log:       {s['log']}")
        if skipped:
            print(f"     Skipped:   {', '.join(skipped)}")
    print("=" * 60)

    all_pass = all(r["status"] == "PASS" for r in all_results)
    return 0 if all_pass else 1


def main():
    args = parse_args()
    setup_logging()

    # 解析并验证配置文件
    config_paths = [resolve_config(p) for p in args.configs]
    for p in config_paths:
        if not os.path.isfile(p):
            logger.error("配置文件不存在: %s", p)
            sys.exit(1)

    # 验证 Python 解释器
    for env_name, python_path in ENV_PYTHON.items():
        if not os.path.isfile(python_path):
            logger.error("Python 解释器不存在: %s (%s)", python_path, env_name)
            sys.exit(1)

    # dry-run 模式
    if args.dry_run:
        print("DRY RUN - 将执行以下命令:\n")
        for config_path in config_paths:
            print(f"--- {os.path.basename(config_path)} ---")
            for step in PIPELINE_STEPS:
                python = ENV_PYTHON[step["env"]]
                cmd = f"{python} {step['script']} --config {config_path}"
                print(f"  {cmd}  [{step['env']}]")
            print()
        return

    logger.info("启动流水线: %d 个配置, max_workers=%d", len(config_paths), args.max_workers)

    all_results = []
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {
            executor.submit(run_config, cp, args.timeout): cp
            for cp in config_paths
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                all_results.append(result)
            except Exception as e:
                config_path = futures[future]
                logger.error("[%s] 未预期的异常: %s", os.path.basename(config_path), e)
                all_results.append({
                    "config": os.path.splitext(os.path.basename(config_path))[0],
                    "status": "FAIL",
                    "results": [],
                })

    sys.exit(print_summary(all_results))


if __name__ == "__main__":
    main()
