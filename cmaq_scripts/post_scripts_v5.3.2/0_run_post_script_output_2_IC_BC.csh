#! /bin/csh -f

setenv CCTM_WORKDIR /program/rain/Build_CMAQ/CMAQ_Project/CCTM/scripts
# 获取当前脚本所在路径，记录下来，否则调用其他脚本时，出现找不到文件
set script_path = /program/rain/Build_CMAQ/CMAQ_Project/CCTM/devin_cmaq_scripts/post_scripts_v5.3.2
set script_path = /program/rain/Build_CMAQ/CMAQ_Project/CCTM/devin_cmaq_scripts/post_scripts_v5.3.2
#初始化cmaq的相关变量
set compiler = intel
# 始终从 CCTM_WORKDIR 推导 CMAQ 根目录，不能从部署脚本目录上溯：后者在
# devin_cmaq_scripts/ 内，三级父目录并不是 CMAQ 源码树。
if ( $?CCTM_WORKDIR ) then
    setenv CMAQ_HOME ${CCTM_WORKDIR}/../../
else if ( ! $?CMAQ_HOME ) then
    echo "Error: CCTM_WORKDIR and CMAQ_HOME are both unset"
    exit 1
endif
if ( ! -f "${CMAQ_HOME}/config_cmaq.csh" ) then
    echo "Error: CMAQ config not found: ${CMAQ_HOME}/config_cmaq.csh"
    exit 1
endif
cd "$CMAQ_HOME"
source ./config_cmaq.csh
if ( $status != 0 ) exit $status
cd $script_path

#> Set General Parameters for Configuring the Simulation
setenv VRSN "v532"
setenv PROC "mpi"
setenv MECH "cb6r3_ae7_aq"
setenv APPL "GD"

setenv LAYER "-1"
setenv DOMAIN "D2"
setenv CASE_NAME "base"
# 主要指气象数据mcip，即该目录下，有emis,mcip,ocean等文件夹。
setenv INPDIR "/bigdata/CMAQ_input/devin/GD/2022_268X202/"
setenv BEGIN_DATE "2021-12-27"
setenv END_DATE "2022-01-31"

setenv OUTPUT_COMBINE_ACONC_FILE "T"
setenv OUTPUT_COMBINE_DEP_FILE "F"
setenv COMBINE_DIR "/mnt/167/devin/cmaq_output/D2/202201"
setenv CCTMOUTDIR_ROOT "/home/devin/cmaq_output/base"
setenv KEEP_18SPECIES_ONLY "T"
setenv INCLUDE_WRF "F"
setenv OUTPUT_BY_YEARMONTH "F"
setenv KEEP_COMBINE_FILE "T"
setenv CLEANUP_CCTM_OUTPUT "F"

setenv TSHIFT "F"
setenv HOUR_OFFSET "8"

setenv CONVERT2DAILY "T"
setenv OUTPUT_DAILY_MAP "T"
setenv BOUNDARY_FILE "/program/software/PanoplyJ/boundary/gd_cities.shp"
setenv PLOT_POLLUTANT "O3_MDA8"
setenv BASELINE_FILE "/mnt/167/devin/cmaq_output/D2/202201/Daily_COMBINE_ACONC_v532_D2_base_GD_all_layers_2021-12-27_2022-01-31_18species.nc"


setenv OUTPUT_IC "T"
setenv OUTPUT_BC "T"
setenv IC_OUTPUT_DIR "/bigdata/CMAQ_input/devin/GD/2022_268X202/icon/devin/D3"
setenv BC_OUTPUT_DIR "/bigdata/CMAQ_input/devin/GD/2022_268X202/bcon/devin/D3"

# COPY_SPEC_DEF:是否把本目录(0_run_post_script.csh 同级)spec_def_files/SpecDef_${MECH}_all_layers.txt
# 覆盖拷贝到 $CMAQ_HOME/POST/combine/scripts/spec_def_files/ 下(combine 的 SPEC_CONC 从该处读取)。
# F=不拷贝(用目标目录已有文件);T=覆盖替换。默认 F。
setenv COPY_SPEC_DEF "F"

# ===== combine 可执行文件校验 + spec 定义文件同步 =====
# combine 用 $CMAQ_HOME/POST/combine/scripts/BLD_combine_${VRSN}_${compilerString}/combine_${VRSN}.exe
# 处理(见 1_run_combine_aconc.csh 的 BINDIR/EXEC);CMAQ_HOME 由文件开头的 config_cmaq.csh 解析,
# 编译过 CMAQ 的部署机上必有定义。此处提前校验,避免 combine 阶段才报错;缺失仅告警不中断。
# 注:模板用 $compiler(=intel),与 1_run_combine_aconc.csh 里的 compilerString 等价。
setenv COMBINE_BINDIR $CMAQ_HOME/POST/combine/scripts/BLD_combine_${VRSN}_${compiler}
setenv COMBINE_EXE ${COMBINE_BINDIR}/combine_${VRSN}.exe
if ( -e ${COMBINE_EXE} ) then
    echo "  ✓ combine 可执行文件: ${COMBINE_EXE}"
else
    echo "  ⚠ combine 可执行文件不存在: ${COMBINE_EXE}"
    echo "    请确认 CMAQ_HOME 指向含 POST/combine/scripts 的源码树,并已编译生成 combine_${VRSN}.exe"
endif


if ( ${COPY_SPEC_DEF} == T ) then
    set SPEC_SRC = ${script_path}/spec_def_files/SpecDef_${MECH}*
    set SPEC_DST_DIR = $CMAQ_HOME/POST/combine/scripts/spec_def_files
    cp -f $SPEC_SRC $SPEC_DST_DIR/
    echo "  ✓ 已覆盖拷贝 spec 定义文件: $SPEC_SRC -> $SPEC_DST_DIR/"
endif


if ((! $?COMBINE_DIR) || ("$COMBINE_DIR" == "")) then
   setenv POSTDIR    ${CCTMOUTDIR_ROOT}/post
else
   setenv POSTDIR $COMBINE_DIR
endif
setenv RUNID  ${VRSN}_${DOMAIN}_${CASE_NAME}_${APPL}

if ( $LAYER == -1 ) then
   setenv LAYER_NAME all_layers
else
   setenv LAYER_NAME layer_${LAYER}
endif

if ( ${OUTPUT_BY_YEARMONTH} == F  ) then
    setenv OUTFILE ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${BEGIN_DATE}_${END_DATE}.nc
else
    set YEAR = `date -ud "${END_DATE}" +%Y`
    set MONTH = `date -ud "${END_DATE}" +%m`
    setenv OUTFILE ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_$YEAR${MONTH}.nc
endif

cd $script_path
echo "当前目录：$script_path"

# =============================Output Initial and Boundary Condition=========================================
#提取当前层的结果作为下一层的输入
# 提取 DOMAIN 中的数字部分
set num = `echo $DOMAIN | sed 's/[^0-9]//g'`
set prefix = `echo $DOMAIN | sed 's/[0-9]*$//'`
# 数字加一
@ new_num = $num + 1
setenv SUB_DOMAIN  "${prefix}${new_num}"
echo "SUB_DOMAIN is ${SUB_DOMAIN}"

 if ( ${OUTPUT_IC} == T  ) then
   echo "Start to output boundary condition..."
   csh 5_run_bcon.csh
   csh 5_run_bcon_D3_155X122.csh
   echo "End to output boundary condition..."
 endif

 if ( ${OUTPUT_BC} == T  ) then
   echo "Start to output initial condition..."
   csh 6_run_icon_loop.csh
   csh 6_run_icon_loop_D3_155X122.csh
   echo "End to output initial condition..."
 endif
# ============================Output Initial and Boundary Condition=========================================

# =============================COMBINE Data========================================
#> COMBINE Data
setenv EXTRACT_FILE $OUTFILE
if ( ${OUTPUT_COMBINE_ACONC_FILE} == T  ) then
   echo "Start to combine aconc data..."
   csh 1_run_combine_aconc.csh
   set combine_status = $status
   if ( $combine_status != 0 ) then
      echo "Error: ACONC combine failed (exit code: $combine_status)"
      exit $combine_status
   endif
   echo "End to combine aconc data..."

   if ( ${KEEP_18SPECIES_ONLY} == T  ) then
      echo "Start to extract 18 species data..."
#     csh 2_extract_18species_by_nco.csh
#      set output_file = `csh 2_extract_18species_by_nco.csh | tail -n 1` # 这个不会输出脚本的其他echo内容
      csh 2_extract_18species_by_nco.csh > tmp_2_extract_18species_by_nco_output.log
      set extract_status = $status
      cat tmp_2_extract_18species_by_nco_output.log
      if ( $extract_status != 0 ) then
         rm -f tmp_2_extract_18species_by_nco_output.log
         echo "Error: 18-species extraction failed (exit code: $extract_status)"
         exit $extract_status
      endif
      set output_file = `tail -n 1 tmp_2_extract_18species_by_nco_output.log`

      echo "get extracted output file from 2_extract_18species_by_nco.csh: $output_file"
      # judge the file whether exists
      if (-e "$output_file") then
         setenv EXTRACT_FILE $output_file
      else
         echo "file not exists: $output_file"
         exit 1
      endif
      echo "End to extract 18 species data..."
      rm -f tmp_2_extract_18species_by_nco_output.log
   endif

   if ( ${TSHIFT} == T  ) then
      echo "Start to convert UTC time to local time..."
      csh 3_tolocaltime.csh
      echo "End to convert UTC time to local time..."
   endif

   if (${CONVERT2DAILY} == T  ) then
        echo "Start to convert to daily data..."
        set devin_env_path = /program/software/devin_env/bin/activate
        if (-e ${devin_env_path}) then
            source ${devin_env_path}
        else
            conda activate devin_env
        endif
        bash -c "source /program/software/devin_env/bin/activate && python 4_convert2daily.py $EXTRACT_FILE $BEGIN_DATE $END_DATE $HOUR_OFFSET"

        # python 4_convert2daily.py $OUTFILE $BEGIN_DATE $END_DATE $HOUR_OFFSET
        echo "End to convert to daily data..."

        if( ${OUTPUT_DAILY_MAP} == T  ) then
            echo "Start to output daily map..."
            set output_dir = `dirname ${EXTRACT_FILE}`
            set input_file_name = `basename ${EXTRACT_FILE}`
            set daily_ncfile = "${output_dir}/Daily_${input_file_name}"

            if (-e ${daily_ncfile}) then
                 bash -c "source /program/software/devin_env/bin/activate &&  python 7_plot_daily_map.py $daily_ncfile $BASELINE_FILE $BEGIN_DATE $END_DATE $PLOT_POLLUTANT $DOMAIN $CASE_NAME $BOUNDARY_FILE"
#                python 7_plot_daily_map.py $daily_ncfile $BASELINE_FILE $BEGIN_DATE $END_DATE $PLOT_POLLUTANT $DOMAIN $CASE_NAME $BOUNDARY_FILE
            else
                echo "Output file ${output_ncfile} does not exist. Skipping daily map plotting."
            endif
            echo "End to output daily map..."
    endif

    #所有都执行完毕后，如果有保留18物种，就可以删除合并的文件
    if ( "$KEEP_18SPECIES_ONLY" == "T" && -e "$output_file" ) then
    	echo "Delete combined file: $OUTFILE"
   	rm -f "$OUTFILE"
    else if ( "$KEEP_18SPECIES_ONLY" == "T" ) then
    	echo "Extracted file does not exist; keep combined file: $OUTFILE"
    endif

endif

if ( ${OUTPUT_COMBINE_DEP_FILE} == T  ) then
   echo "Start to combine dep data..."
   csh 1_run_combine_dep.csh
   set combine_dep_status = $status
   if ( $combine_dep_status != 0 ) then
      echo "Error: deposition combine failed (exit code: $combine_dep_status)"
      exit $combine_dep_status
   endif
   echo "End to combine dep data..."
endif

# =============================COMBINE Data========================================

# =============================清理 CCTM 输出目录(腾空间)========================================
# 开关:CLEANUP_CCTM_OUTPUT(见上方 toggle 区,默认 T)。F=跳过本段清理。
# 参考 legacy/run_cctm_D3_202209.csh:
# 后处理完成后,若指定的 combine 输出文件已生成,保留 *.cfg 与 CCTM_CGRID* 文件,
# 其余(逐日 CCTM_CONC/ACONC/DRYDEP/WETDEP 等)删除,为后续 case 提供空间。
# 判定的"指定输出文件"用 EXTRACT_FILE,而非 output_file:
#   output_file 只在 KEEP_18SPECIES_ONLY=T 分支内定义;=F 时未定义,直接引用会报 "Undefined variable"。
#   EXTRACT_FILE 始终有值:默认 = OUTFILE(完整 COMBINE_ACONC);KEEP=T 且文件存在时才更新为 18 物种文件。
#   两者均位于 POSTDIR(即 COMBINE_DIR)。
if ( ${CLEANUP_CCTM_OUTPUT} == T ) then
    if ( -e ${EXTRACT_FILE} ) then
        set YEAR = `date -ud "${END_DATE}" +%Y`
        set MONTH = `date -ud "${END_DATE}" +%m`
        set cleanup_dir = ${CCTMOUTDIR_ROOT}/${DOMAIN}/${YEAR}/${MONTH}
        echo "检测到 combine 输出文件 ${EXTRACT_FILE},清理 CCTM 输出目录: ${cleanup_dir}"
        if ( -d ${cleanup_dir} ) then
            find ${cleanup_dir} -type f \
                ! -name "*.cfg" \
                ! -name "CCTM_CGRID*" \
                -delete
            echo "  ✓ 已清理(保留 *.cfg 与 CCTM_CGRID*)"
        else
            echo "  ⚠ 清理目录不存在: ${cleanup_dir}"
        endif
    else
        echo "combine 输出文件不存在: ${EXTRACT_FILE},跳过清理"
    endif
else
    echo "CLEANUP_CCTM_OUTPUT=F,跳过 CCTM 输出目录清理"
endif
# =============================清理 CCTM 输出目录========================================


