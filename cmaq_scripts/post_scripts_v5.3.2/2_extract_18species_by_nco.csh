#!/bin/csh -f


echo "KEEP_18SPECIES_ONLY is ${KEEP_18SPECIES_ONLY}"
echo "OUTPUT_BY_YEARMONTH is ${OUTPUT_BY_YEARMONTH}"
echo "POSTDIR is ${POSTDIR}"
echo "RUNID is ${RUNID}"
echo "LAYER_NAME is ${LAYER_NAME}"
echo "BEGIN_DATE is ${BEGIN_DATE}"
echo "END_DATE is ${END_DATE}"
echo "INCLUDE_WRF is ${INCLUDE_WRF}"
echo "KEEP_COMBINE_FILE is ${KEEP_COMBINE_FILE}"


set START_DATE = ${BEGIN_DATE} 

if ("${KEEP_18SPECIES_ONLY}" == "T") then
     # 提取起止年月
     set start_year = `echo ${BEGIN_DATE}| cut -c1-4`
     set start_month = `echo ${BEGIN_DATE}| cut -c6-7`
     set end_year = `echo ${END_DATE} | cut -c1-4`
     set end_month = `echo ${END_DATE} | cut -c6-7`
     # 转换为整数
     @ year = $start_year
     @ month = $start_month
     # 初始化数组
     set ym_list = ()

     # 构造年月集合
    while ( ( $year < $end_year ) || ( $year == $end_year && $month <= $end_month ) )
        # 格式化为 YYYYMM
        if ( $month < 10 ) then
            set ym = "${year}0${month}"
        else
            set ym = "${year}${month}"
        endif
        # 添加到数组
        set ym_list = ( $ym_list $ym )
        # 增加月份
        @ month++
        if ( $month > 12 ) then
            @ month = 1
            @ year++
        endif
    end


    if ( ${OUTPUT_BY_YEARMONTH} == F  ) then
       set ym_list = ( "${start_year}${end_month}" )
    endif

    foreach ym ( $ym_list )
        if ( ${OUTPUT_BY_YEARMONTH} == T  ) then
           # 输入文件
           set infile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${ym}.nc  #"/home/devin/cmaq_output/fj2zero/POST/COMBINE_ACONC_v532_D1_fj2zero_PRD_all_layers_202209.nc"
           # 输出文件
           set outfile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${ym}_18species.nc  #"/home/devin/cmaq_output/fj2zero/POST/COMBINE_ACONC_v532_D1_fj2zero_PRD_all_layers_202209_18species.nc"
        else
            # 输入文件
           set infile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${START_DATE}_${END_DATE}.nc  #"/home/devin/cmaq_output/fj2zero/POST/COMBINE_ACONC_v532_D1_fj2zero_PRD_all_layers_202209.nc"
           # 输出文件
           set outfile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${START_DATE}_${END_DATE}_18species.nc  #"/home/devin/cmaq_output/fj2zero/POST/COMBINE_ACONC_v532_D1_fj2zero_PRD_all_layers_202209_18species.nc"
        endif

        # 输入文件
#        set infile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${ym}.nc  #"/home/devin/cmaq_output/fj2zero/POST/COMBINE_ACONC_v532_D1_fj2zero_PRD_all_layers_202209.nc"
        # 输出文件
#        set outfile = ${POSTDIR}/COMBINE_ACONC_${RUNID}_${LAYER_NAME}_${ym}_18species.nc  #"/home/devin/cmaq_output/fj2zero/POST/COMBINE_ACONC_v532_D1_fj2zero_PRD_all_layers_202209_18species.nc"
        # 是否包含 WRF 变量（设为 "T" 或 "F"）
        #set include_wrf = "T"
        if ( ! -f $infile ) then
             echo "ERROR：${infile} not exist"
             exit 1
        endif
        echo "Extract file: ${infile}"
        # 基本化学变量列表
        set base_vars = (HNO3 H2O2 N2O5 NO2 FORM HONO NO O3 SO2 NH3 OH ISOP TERP ASO4IJ ANO3IJ ANH4IJ ASOCIJ PM25_TOT NOX VOC O3_UGM3)
        # WRF 变量列表
#       set wrf_vars = (RH SFC_TMP PBLH SOL_RAD precip WSPD10 WDIR10)
        set wrf_vars = (RH SFC_TMP PBLH SOL_RAD precip WSPD10 WDIR10 GLW PRSFC Q2)
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
           if ( ${KEEP_COMBINE_FILE} != T  ) then
       	       echo "Delete file..."
               rm -f $infile
           endif
        endif
        echo "finish extracting file!"
        # 输出路径，以便其他脚本可以直接接受这个返回路径
        echo $outfile 
    end
endif

