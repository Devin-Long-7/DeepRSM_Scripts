#!/bin/csh -f
# CST00选择性初始场实验：所有日常参数集中在此配置。
# 路径可写绝对路径，或相对于本配置所在目录。

# ===== 日期、实验配置及输入清单 =====

# 目标模拟日期，均为北京时间CST自然日；空格分隔。每一天从前一UTC日16时开始运行24小时。
setenv TARGET_DATES "2022-09-06 2022-09-13 2022-09-14 2022-09-16 2022-09-19"

# 要执行的实验配置，空格分隔；只跑少数配置时删去其余名称。
# C/R为连续场/重置场端点；C_NO2只换NO2；R_without_NO2将R中的NO2换回C。
# C_other_N/C_OVOC/C_O3/C_rest分别替换其他氮、OVOC、臭氧及剩余状态变量。
setenv EXPERIMENT_CASES "C R C_NO2 R_without_NO2 C_other_N C_OVOC C_O3 C_rest"

# NetCDF准备和后处理使用的Python解释器，要求Python>=3.8及相关依赖；可改为环境中的绝对路径。
setenv PYTHON_CMD "/program/software/devin_env/bin/python3"

# 整批模拟成功后是否自动汇总臭氧：Y开启，N关闭；关闭后仍可用--post-only单独处理。
setenv ENABLE_POST_PROCESS "Y"

# 参考的CST00两段CMAQ运行模板；程序复制并填充参数，不修改原模板。
setenv TEMPLATE_FILE "assets/run_cctm_template.csh"

# 模型输出根目录；每次批次在其下创建独立batch_XXXX子目录，保存原始输出。
setenv OUTDIR_BASE "/home/devin/cmaq_output/carryover_species_experiments"

# 初始场数据清单CSV：每行填写CST日期、排放情景、连续UTC16场、实际重置UTC16场和排放NML路径。
setenv INPUT_FIELDS_FILE "initial_fields.csv"

# 九城市行政边界GeoJSON；后处理按格点中心建立城市掩膜并统计O3。
setenv BOUNDARY_FILE "assets/guangdong_cities.json"

# ===== 物种分组：未列出的完整状态字段自动归入rest =====

# 单独检验的NO2组；只交换完整三维NO2场，不联动NO或其他氮物种。
setenv GROUP_NO2 "NO2"

# 其他氧化态/反应性氮及其储库组，含PAN类、有机硝酸盐、气相及颗粒硝酸盐。
# 不含NO2；NH3/NH4默认留在rest，因此本组不等同于完整反应性氮。候选缺失会记录，不补零。
setenv GROUP_OTHER_N "NO NO3 HONO HNO3 N2O5 PNA PAN PANX OPAN NTR1 NTR2 INTR CRON CLNO2 CLNO3 MTNO3 H2NO3PIJ H2NO3PK ANO3I ANO3J ANO3K AMTNO3J"

# 选定的含氧有机物组，包括醛、酮、酸和有机过氧化物；使用CB6R3机制物种名。
# 含氮有机物放在OTHER_N组，各组不能重叠；未列出的有机物或自由基归入rest。
setenv GROUP_OVOC "FORM ALD2 ALDX GLY MGLY GLYD ACET KET PACD AACD FACD MEOH ETOH ROOH MEPX ISPD HPLD"

# 原有臭氧组，用于区分初始O3留存与初始前体物变化的作用。
setenv GROUP_O3 "O3"

# ===== CMAQ资源、网格、输入和输出设置（参考IC-RB-CST00_scripts）=====

# CMAQ工程的CCTM工作目录；供运行模板设置WORKDIR，不是本批处理目录。
setenv CCTM_WORKDIR "/program/rain/Build_CMAQ/CMAQ_Project/CCTM/scripts"

# MPI启动程序所在目录；生成的运行脚本将其加入PATH以选择正确mpiexec。
setenv MPI_BIN "/opt/intel/impi/2019.0.117/intel64/bin"

# Intel MPI通信方式；shm仅使用共享内存，适用于同一节点运行，多节点须按服务器环境调整。
setenv I_MPI_FABRICS "shm"

# 每个MPI进程的OpenMP线程数；1表示每进程单线程。
setenv OMP_NUM_THREADS "1"

# CMAQ版本标识，用于可执行文件及配置文件名；v532对应CMAQ v5.3.2。
setenv VRSN "v532"

# 计算模式：mpi表示并行；模板也支持serial串行模式。
setenv PROC "mpi"

# 化学机制名称；必须与BLD内的可执行程序、机理NML及初始场一致。
setenv MECH "cb6r3_ae7_aq"

# 模拟域代号，D3为本次内层域；用于模板域设置。
setenv DOMAIN "D3"

# 运行标识及输出文件名前缀；PRD对应CCTM_ACONC_PRD_YYYYJJJ.nc等。
setenv APPL "PRD"

# CMAQ构建目录，包含CCTM_v532.exe、化学机制NML、光解资料和CCTM配置。
setenv BLD "/program/rain/Build_CMAQ/CMAQ_Project/CCTM/scripts/BLD_CCTM_v532_intel"

# CMAQ输入资料根目录；具体气象、排放和边界目录由下方独立参数指定。
setenv INPDIR "/bigdata/CMAQ_input/devin/PRD/2022"

# MPI水平方向列分区数；总进程数=NPCOL×NPROW，当前8×4=32。
setenv NPCOL "8"

# MPI水平方向行分区数；需与机器资源及网格大小匹配。
setenv NPROW "4"

# GRIDDESC中的网格名称；须与初始场、气象和排放的实际网格一致。
setenv GRID_NAME "SD_2013"

# IO/API网格描述文件路径；内含GRID_NAME对应投影和网格定义。
setenv GRIDDESC "/bigdata/CMAQ_input/devin/PRD/2022/mcip/D3/GRIDDESC"

# 模拟垂直层数；当前14层，须与初始场VGLVLS层界及气象一致。
setenv NZ "14"

# 瞬时浓度CONC输出物种；ALL保留全部，避免丢失后续机制分析所需变量。
setenv CONC_SPCS "ALL"

# 时段平均浓度ACONC输出物种；ALL保留全部，臭氧后处理读取该输出。
setenv AVG_CONC_SPCS "ALL"

# 瞬时CONC输出的起止层号（从1开始，含首尾）；1 14表示全部14层。
setenv CONC_BLEV_ELEV "1 14"

# 平均ACONC输出的起止层号；后处理读取第一层，其他层保留供垂直分析。
setenv ACONC_BLEV_ELEV "1 14"

# 最大同步时间步长，单位秒；300为上限，不是输出间隔。
setenv CTM_MAXSYNC "300"

# 最小同步时间步长，单位秒；60为下限，保持与参考模拟一致。
setenv CTM_MINSYNC "60"

# 控制同步时间步长计算的sigma层阈值，无量纲；0.7沿用参考模板设置。
setenv SIGMA_SYNC_TOP "0.7"

# 平流计算的目标Courant数，无量纲；0.95沿用参考模拟，影响时间步选择。
setenv CTM_ADV_CFL "0.95"

# 气溶胶诊断APMDIAG输出的起止层号；1 14保留全部层。
setenv APMDIAG_BLEV_ELEV "1 14"

# 边界条件目录；各UTC运行日读取BCON_YYYYJJJ，同一天所有实验共用。
setenv BC_PATH "/bigdata/CMAQ_input/devin/PRD/bcon/D3_base"

# MCIP气象目录；按UTC日期读取GRID/MET文件，所有实验共用同一气象。
setenv MET_PATH "/bigdata/CMAQ_input/devin/PRD/2022/mcip/D3"

# 排放控制所需的空间掩膜文件；其中区域名须匹配输入清单指定的EmissCtrl NML。
setenv CMAQ_MASKS "/bigdata/CMAQ_input/devin/PRD/2022/ocean/D3/D3_cmaq_masks"

# 海洋/海岸掩膜输入文件路径，供海盐等模型过程使用。
setenv OCEAN_1_PATH "/bigdata/CMAQ_input/devin/PRD/2022/ocean/D3/oceanfile"

# 人为网格排放目录；排放文件名由EM_AV_PREFIX与代表日儒略日期拼接。
setenv AV_EMIS_DIR "/bigdata/CMAQ_input/devin/PRD/2022/emis/D3"

# 离线MEGAN生物源排放目录；排放文件名按真实UTC日期拼接。
setenv BV_EMIS_DIR "/bigdata/CMAQ_input/devin/PRD/2022/emis/D3/MEGAN"

# 网格排放流数量；2对应人为GRIDDED_AV与生物源GRIDDED_BV。
setenv N_EMIS_GR "2"

# 人为排放代表月，YYYY-MM；用该月首个周五/周六/周日代表工作日/周六/周日。
# 即使分段跨入前一月仍沿用此代表月，不按分段日期自动切换清单。
setenv EMIS_MONTH "2022-09"

# 人为排放文件名前缀，后接代表日YYYYJJJ；当前无额外后缀。
setenv EM_AV_PREFIX "comb_ArearateAB_cn03_"

# 生物源排放文件名前缀，后接实际UTC日YYYYJJJ和MEGAN_SUFFIX。
setenv MEGAN_PREFIX "MEGANv32.PRD_3km."

# 生物源排放文件名后缀；与MEGAN_PREFIX及实际UTC日期共同组成完整文件名。
setenv MEGAN_SUFFIX ".BDSNP.ncf"
