#!/usr/bin/env python3
"""Render one single-segment CCTM run script from the validated template.

The existing lead-time template contains the complete CMAQ configuration.  A
rendered segment only changes dates, output/name paths, the EmissCtrl file,
and the restart used on its first simulated day.  Keeping this transformation
explicit makes it possible to inspect every generated script before running
CMAQ.
"""

from __future__ import annotations

import argparse
import os
import re
import stat
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--case-name", required=True)
    parser.add_argument("--appl", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--sttime", required=True)
    parser.add_argument("--nsteps", required=True)
    parser.add_argument("--emissctrl", required=True, type=Path)
    parser.add_argument("--restart-dir", required=True)
    parser.add_argument("--restart-jday", required=True)
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--icbc-root", required=True)
    parser.add_argument("--cmaq-home", required=True)
    parser.add_argument("--bld", required=True)
    parser.add_argument("--log-dir", required=True)
    return parser.parse_args()


def replace_once(text: str, pattern: str, replacement: str, label: str) -> str:
    text, count = re.subn(
        pattern,
        lambda _match: replacement,
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError(f"template line not found for {label}: {pattern}")
    return text


def restart_block(args: argparse.Namespace, start_jday: str) -> str:
    # This block is inserted after the template's normal initial-condition
    # selection.  It therefore overrides ICON/restart defaults only on the
    # first date of this segment; later dates use the segment's own output.
    media = (
        f"{args.restart_dir}/CCTM_MEDIA_CONC_{args.appl}_{args.restart_jday}.nc"
    )
    return (
        f"  if ( $TODAYJ == {start_jday} ) then\n"
        f"    set ICpath = {args.restart_dir}\n"
        f"    setenv ICFILE CCTM_CGRID_{args.appl}_{args.restart_jday}.nc\n"
        f"    if ( -e {media} ) then\n"
        f"      setenv INIT_MEDC_1 {media}\n"
        f"    else\n"
        f"      setenv INIT_MEDC_1 notused\n"
        f"    endif\n"
        f"    setenv INITIAL_RUN N\n"
        f"    setenv NEW_START FALSE\n"
        f"  endif\n\n"
    )


def render(args: argparse.Namespace) -> str:
    if not args.template.is_file():
        raise ValueError(f"template not found: {args.template}")
    if not args.emissctrl.is_file():
        raise ValueError(f"EmissCtrl not found: {args.emissctrl}")

    text = args.template.read_text(encoding="utf-8")
    text = replace_once(
        text,
        r"^[ \t]*set[ \t]+CASE_NAME[ \t]*=.*$",
        f" set CASE_NAME   = {args.case_name}",
        "CASE_NAME",
    )
    text = replace_once(
        text,
        r"^[ \t]*set[ \t]+APPL[ \t]*=.*$",
        f" set APPL  = {args.appl}",
        "APPL",
    )
    text = replace_once(
        text,
        r"^[ \t]*setenv[ \t]+CMAQ_HOME[ \t]+.*$",
        f"setenv CMAQ_HOME {args.cmaq_home}",
        "CMAQ_HOME",
    )
    text = replace_once(
        text,
        r"^[ \t]*set[ \t]+BLD[ \t]*=.*$",
        f" set BLD = {args.bld}",
        "BLD",
    )
    text = replace_once(
        text,
        r"^[ \t]*setenv[ \t]+INPDIR[ \t]+.*$",
        f" setenv INPDIR {args.input_root}",
        "INPDIR",
    )
    text = replace_once(
        text,
        r"^[ \t]*set[ \t]+icbc_root[ \t]*=.*$",
        f"set icbc_root = {args.icbc_root}",
        "icbc_root",
    )
    text = replace_once(
        text,
        r"^[ \t]*setenv[ \t]+OUTDIR[ \t]+/.*$",
        f" setenv OUTDIR  {args.out_root}",
        "OUTDIR",
    )
    text = replace_once(
        text,
        r"^[ \t]*setenv[ \t]+LOGDIR[ \t]+.*$",
        f" setenv LOGDIR  {args.log_dir}",
        "LOGDIR",
    )
    text = replace_once(
        text,
        r"^[ \t]*set[ \t]+firstday[ \t]*=.*$",
        f' set firstday  = "{args.start_date}"',
        "firstday",
    )
    text = replace_once(
        text,
        r"^[ \t]*set[ \t]+START_DATE[ \t]*=.*$",
        f'set START_DATE = "{args.start_date}"',
        "START_DATE",
    )
    text = replace_once(
        text,
        r"^[ \t]*set[ \t]+END_DATE[ \t]*=.*$",
        f'set END_DATE   = "{args.end_date}"',
        "END_DATE",
    )
    month = args.start_date[5:7]
    text = replace_once(
        text,
        r"^[ \t]*set[ \t]+month[ \t]*=.*$",
        f"set month = '{month}'",
        "month",
    )
    text = replace_once(
        text,
        r"^[ \t]*set[ \t]+STTIME[ \t]*=.*$",
        f" set STTIME     = {args.sttime}",
        "STTIME",
    )
    text = replace_once(
        text,
        r"^[ \t]*set[ \t]+NSTEPS[ \t]*=.*$",
        f" set NSTEPS     = {args.nsteps}",
        "NSTEPS",
    )
    text = replace_once(
        text,
        r"^[ \t]*setenv[ \t]+EMISSCTRL_NML[ \t]+.*$",
        f"  setenv EMISSCTRL_NML {args.emissctrl}",
        "EMISSCTRL_NML",
    )

    start_jday = f"{args.start_date[:4]}{__import__('datetime').datetime.strptime(args.start_date, '%Y-%m-%d').strftime('%j')}"
    marker = re.compile(
        r"(?m)^(?P<indent>[ \t]*)setenv[ \t]+OMI[ \t]+\$BLD/OMI_1979_to_2019\.dat[ \t]*$"
    )
    match = marker.search(text)
    if match is None:
        raise ValueError("template OMI line not found; restart injection is unsafe")
    text = text[: match.start()] + restart_block(args, start_jday) + text[match.start() :]
    return text


def main() -> int:
    args = parse_args()
    rendered = render(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    mode = args.output.stat().st_mode
    args.output.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
