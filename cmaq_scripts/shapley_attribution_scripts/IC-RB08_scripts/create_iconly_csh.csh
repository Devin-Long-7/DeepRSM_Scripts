#!/bin/bash
# Generate a C10 IC-only run script for a region, from the canonical prd2zero_iconly script.
# Usage: ./create_iconly_csh.csh <region>   e.g. ./create_iconly_csh.csh gz
# Output: run_cctm_D3_202209_<region>2zero_iconly.csh
#   CASE_NAME = <region>2zero_iconly
#   C11_CASE  = <region>2zero
# All C10 scenarios share EmissCtrl_..._base.nml (no per-region nml needed).

set -e
region="$1"
if [ -z "$region" ]; then
   echo "Usage: $0 <region> (e.g. prd, gz, sz, zh, fs, jm, zq, hz, dg, zs)"
   exit 1
fi

src="run_cctm_D3_202209_prd2zero_iconly.csh"
dst="run_cctm_D3_202209_${region}2zero_iconly.csh"
if [ "$src" = "$dst" ]; then
   echo "Canonical already is the ${region} script: $src (nothing to generate)"
   exit 0
fi
if [ ! -f "$src" ]; then
   echo "ERROR: canonical source not found: $src"
   exit 1
fi

cp "$src" "$dst"
# Whitespace-tolerant: capture the "set VAR <sp>= <sp>" prefix, replace only the value.
sed -i -E "s/(set CASE_NAME[[:space:]]+=[[:space:]]*)prd2zero_iconly/\1${region}2zero_iconly/" "$dst"
sed -i -E "s/(set C11_CASE[[:space:]]+=[[:space:]]*)prd2zero/\1${region}2zero/" "$dst"
chmod +x "$dst"
echo "Created $dst (CASE_NAME=${region}2zero_iconly, C11_CASE=${region}2zero)"
