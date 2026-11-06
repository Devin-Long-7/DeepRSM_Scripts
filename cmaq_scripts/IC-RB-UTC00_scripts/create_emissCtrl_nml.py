#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从基础NML模板 + CSV缩放规则 生成情景特定的EmissCtrl NML文件.

用法:
    python3 create_emissCtrl_nml.py --case-name oos3 --case-type standard --output generated/EmissCtrl_cb6r3_ae7_aq_oos3.nml
"""

import argparse
import csv
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
NML_CONFIG_DIR = os.path.join(SCRIPT_DIR, 'nml_config')


def read_scaling_rules(case_name):
    csv_path = os.path.join(NML_CONFIG_DIR, 'scaling_rules.csv')
    if not os.path.isfile(csv_path):
        print(f"Error: scaling rules file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    rules = []
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['case_name'] == case_name:
                rules.append(row)
    return rules


def read_stream_families(case_type):
    csv_path = os.path.join(NML_CONFIG_DIR, 'stream_families.csv')
    if not os.path.isfile(csv_path):
        print(f"Error: stream families file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    with open(csv_path, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['case_type'] == case_type:
                members = row['members'].split(';')
                return row['family_name'], members
    return None, None


def format_rule_line(region, stream_label, chemical_family, phase, scale_factor):
    return f" '{region}', '{stream_label}'         ,'ALL'     ,'{chemical_family}'          ,'{phase}'  ,{scale_factor},'UNIT','m',"


def format_stream_members(members):
    quoted = [f"'{m}'" for m in members]
    return ','.join(quoted)


def generate_nml(case_name, case_type, output_path):
    # Read base template
    template_path = os.path.join(NML_CONFIG_DIR, 'EmissCtrl_base.nml')
    with open(template_path) as f:
        content = f.read()

    # Get scaling rules
    rules = read_scaling_rules(case_name)

    # Format rule lines
    if rules:
        rule_lines = []
        for r in rules:
            line = format_rule_line(
                r['region'], r['stream_label'],
                r['chemical_family'], r['phase'],
                r['scale_factor']
            )
            rule_lines.append(line)
        rules_text = '\n'.join(rule_lines)
    else:
        rules_text = ''

    content = content.replace('!>>>CUSTOM_SCALING_RULES<<<', rules_text)

    # Get stream families
    family_name, members = read_stream_families(case_type)
    if family_name is None:
        print(f"Error: case_type '{case_type}' not found in stream_families.csv", file=sys.stderr)
        sys.exit(1)

    members_text = format_stream_members(members)
    content = content.replace('!>>>STREAM_FAMILY_MEMBERS<<<', members_text)

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(content)

    print(f"Generated: {output_path} ({len(rules)} custom rules, {case_type} type)")


def main():
    parser = argparse.ArgumentParser(description='Generate EmissCtrl NML from template + CSV')
    parser.add_argument('--case-name', required=True, help='Case name (e.g. oos3, cn2zero)')
    parser.add_argument('--case-type', required=True, choices=['standard', 'sector'],
                        help='Case type: standard or sector')
    parser.add_argument('--output', required=True, help='Output NML file path')
    args = parser.parse_args()

    generate_nml(args.case_name, args.case_type, args.output)


if __name__ == '__main__':
    main()
