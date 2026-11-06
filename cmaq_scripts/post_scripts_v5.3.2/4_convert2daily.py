# -*- coding: utf-8 -*-

import datetime
from datetime import datetime
from esil.date_helper import get_days_in_month
import os
from esil.netcdf_helper import convert_hr2daily_data
from tqdm.auto import tqdm
import sys

# 检查参数数量
if len(sys.argv) < 5:
    print("Usage: script.py <OUTFILE> <BEGIN_DATE> <END_DATE> <HOUR_OFFSET>")
    sys.exit(1)

# 获取参数
source_ncfile = sys.argv[1]  # 第一个参数
start_date_str = sys.argv[2]  # "2022-08-27"
end_date_str = sys.argv[3]  # "2022-08-27"

# 检查日期格式
try:
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
except ValueError:
    print("Invalid date format. Please use YYYY-MM-DD.")
    sys.exit(1)

# 检查 hour_offset 是否为整数
try:
    hour_offset = int(sys.argv[4])
except ValueError:
    print("Invalid hour_offset. Please provide an integer value.")
    sys.exit(1)

layer_index = 0
output_dir = os.path.dirname(source_ncfile)
if not output_dir:
    output_dir = "."

input_file_name = os.path.basename(source_ncfile)
output_ncfile = os.path.join(output_dir, f"Daily_{input_file_name}")
if os.path.exists(output_ncfile):
    overwrite = sys.argv[5] if len(sys.argv) > 5 else False
    if not overwrite:        
        print(f"Output file {output_ncfile} already exists. Exiting...")
        sys.exit(0)  # 直接正常退出
# 将日期格式化为字符串
start_date_str_fmt = start_date.strftime("%Y%m%d")
end_date_str_fmt = end_date.strftime("%Y%m%d")

# 调用 convert_hr2daily_data 函数
output_daily_file = convert_hr2daily_data(
    source_ncfile=source_ncfile,
    output_ncfile=output_ncfile, 
    start_date=start_date_str_fmt,
    end_date=end_date_str_fmt,
    layer_index=layer_index,
    hour_offset=hour_offset,
    previous_or_next_ncfile=None,
    output_file_format="NETCDF3_CLASSIC",
)

print("done")
