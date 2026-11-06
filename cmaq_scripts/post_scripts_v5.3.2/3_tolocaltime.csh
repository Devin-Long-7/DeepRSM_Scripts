#!/bin/csh -f

#set HOUR_OFFSET = 8
#set POSTDIR = /home/devin/cmaq_output/base/post
#set BEGIN_DATE = 2022-08-27
#set END_DATE = 2022-08-29
#set INPFILE = /home/devin/cmaq_output/base/post/COMBINE_ACONC_v532_D1_base_PRD_all_layers_2022-08-27_2022-08-29.nc
#set OUTFILE = /home/devin/cmaq_output/base/post/COMBINE_ACONC_v532_D1_base_PRD_all_layers_2022-08-27_2022-08-29_tshift_bj.nc

#unlimit
if ("$BEGIN_DATE" == "") then
    echo "ERROR: BEGIN_DATE is not set."
    exit 1
endif
if ("$END_DATE" == "") then
    echo "ERROR: END_DATE is not set."
    exit 1
endif
if ("$HOUR_OFFSET" == "") then
    echo "ERROR: HOUR_OFFSET is not set."
    exit 1
endif
if ("$OUTFILE" == "") then
    setenv INPFILE /home/devin/cmaq_output/prd2zero/post/COMBINE_ACONC_v532_D1_prd2zero_PRD_all_layers_202209.nc    
else
    setenv INPFILE $OUTFILE
endif
# 使用字符串替换生成新的文件路径
set OUTFILE = `echo $INPFILE | sed 's/.nc/_tshift_bj.nc/'`

echo "OUTFILE is ${OUTFILE}"
echo "HOUR_OFFSET is ${HOUR_OFFSET}"
echo "POSTDIR is ${POSTDIR}"
echo "BEGIN_DATE is ${BEGIN_DATE}"
echo "END_DATE is ${END_DATE}"

# 设置默认的 m3tshift 路径
set M3TSHIFT_PATH = "/program/rain/Build_CMAQ/LIBRARIES/ioapi/Linux2_x86_64ifort/m3tshift"  # 替换为实际的路径

# 日期转换
set start_date = `date -ud "${BEGIN_DATE}" +%Y%j`
set end_date = `date -ud "${END_DATE}" +%Y%j`

# 数学运算
@ temp_hour = 24 - $HOUR_OFFSET
@ diff_days = $end_date - $start_date
@ temp_duration = $diff_days * 24 - 1
@ shift_date = $start_date + 1

# 字符串拼接
set start_hour = "${temp_hour}0000"
set duration = "${temp_duration}0000"


# 打印结果
echo "输入文件: $INPFILE"
echo "输出文件: $OUTFILE"
#INPFILE #输入文件
#2022244 #输入文件起始日期
#160000 #输入文件起始时间	
#2022245 #对应文件起始日期需要转换后的日期，比如往前移8小时，2022244 16:00 应该对应的是2022245 00:00
#000000 #对应文件起始时间需要转换后的时间，即输入文件起始时间 转换后的时间，16:00 → 00:00
#10000  #每个时间点间隔步长
#7190000 # 持续时间长度
#OUTFILE # 输出文件

# 检查 m3tshift 是否在系统路径中
set M3TSHIFT_CMD = `which m3tshift`
if ("$M3TSHIFT_CMD" == "") then    
    echo "m3tshift 未找到，使用指定路径: $M3TSHIFT_PATH"
    set M3TSHIFT_CMD = $M3TSHIFT_PATH
else
    echo "m3tshift 路径: $M3TSHIFT_CMD"
endif

#setenv EXECUTION_ID "m3tshift_run"
#echo "M3TSHIFT_CMD is $M3TSHIFT_CMD"
# 运行 m3tshift
echo "Running m3tshift with the following parameters:"
echo "Input file: ${INPFILE}"
echo "Start date: ${start_date}"
echo "Start hour: ${start_hour}"
echo "Shift date: ${shift_date}"
echo "Duration: ${duration}"
echo "Output file: ${OUTFILE}"

#这里需要重新设置一下环境变量为全局变量
setenv INPFILE ${INPFILE}   
setenv OUTFILE ${OUTFILE} 
#ln -sf $OUTFILE output.nc
#m3tshift  << EOF
$M3TSHIFT_CMD  << EOF
INPFILE
${start_date}
${start_hour}
${shift_date}
000000
10000
${duration}
OUTFILE
EOF

echo "Extract file: ${OUTFILE}"
set infile = ${OUTFILE} 
# 输出文件
set outfile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${BEGIN_DATE}_${END_DATE}_18species_tshift_bj.nc

# 基本化学变量列表
set base_vars = (HNO3 H2O2 N2O5 NO2 FORM HONO NO O3 SO2 NH3 OH ISOP TERP ASO4IJ ANO3IJ ANH4IJ ASOCIJ PM25_TOT NOX VOC)
# WRF 变量列表
set wrf_vars = (RH SFC_TMP PBLH SOL_RAD precip WSPD10 WDIR10)
# 合并变量列表
set varlist = ($base_vars)
if ("${INCLUDE_WRF}" == "T") then
   set varlist = ($varlist $wrf_vars)
endif
# 拼接成逗号分隔的字符串
set varstr = "$varlist[1]"
@ i = 2
while ($i <= $#varlist)
	set varstr = "${varstr},$varlist[$i]"
	@ i++
end
# 调用 ncks，注意：用双引号把 $varstr 包起来
echo "提取变量: $varstr"
ncks -v "$varstr" "$infile" "$outfile"
if ( -e $outfile ) then
   echo "Delete file..."
   rm -f $infile
endif
echo "Success! Finish extracting file!"

