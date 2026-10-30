import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import os
import time
# import logging
from logging.handlers import TimedRotatingFileHandler
import sqlite3
import numpy as np
from esil.log_helper import get_logger
import random
import string
from tqdm import tqdm
# 获取当前脚本所在的目录
script_dir = os.path.dirname(os.path.abspath(__file__))
# 设置新的工作目录
os.chdir(script_dir)

# 创建一个logger
log_name = f'./logs/sqlite_helper.log'
logger = get_logger(log_name)


def validate_data_columns(str_sqlite_db,table_name, data_columns):
    ''' 
    @description: 检查数据列数是否与表的列数匹配
    @param {str} str_sqlite_db: SQLite数据库文件路径
    @param {str} table_name: 表名
    @param {list} data_columns: 数据列名列表
    @return {bool} 成功返回True，失败返回False
    '''
    conn = sqlite3.connect(str_sqlite_db)
    cursor = conn.cursor()
    # 获取表的列数
    cursor.execute(f"PRAGMA table_info({table_name})")
    num_columns = len(cursor.fetchall())
    # 检查数据的列数是否与表的列数匹配
    if len(data_columns) != num_columns:
        logger.error(f"Error: Number of columns in data ({len(data_columns)}) does not match the number of columns in table ({num_columns})")
        return False
    else:
        return True
    
def save_df_to_db(str_sqlite_db,df,table_name,if_exists='replace',index=False,identified_columns=None,use_temp_table=True,batch_size=10000):  #='station_info'
    '''
    @description: 将数据框保存到数据库
    @param {str} str_sqlite_db: SQLite数据库文件路径
    @param {pd.DataFrame} df: 数据框
    @param {str} table_name: 表名
    @param {str} if_exists:replace; append; fail; default='replace' 若存在则覆盖，否则新建;
    @param {str} identified_columns: 索引标签, default=None,若指定数据库表中的主键列名称。通过指定主键列，系统将根据主键列的值来判断是否插入新数据；尚不存在的新记录时，才会将这些新记录插入到数据库表中。已存在的相同记录将不会被重复插入
    @return {bool} 成功返回True，失败返回False
    '''
    try:
        conn = sqlite3.connect(f"{str_sqlite_db}") 
        cursor = conn.cursor()           
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}' COLLATE NOCASE")#COLLATE NOCASE 忽略大小写
        result = cursor.fetchone()
        table_exists = result is not None
        if table_exists:
            is_ok=validate_data_columns(str_sqlite_db,table_name, df.columns.tolist())
            if not is_ok:  
                # 列数不匹配时，重命名当前表
                new_table_name = f'{table_name}_{datetime.now().strftime("%Y%m%d%H%M%S")}'
                cursor.execute(f"ALTER TABLE {table_name} RENAME TO {new_table_name}")
                # 创建新表来存储数据
                df.to_sql(table_name, conn, if_exists=if_exists, index=index)
                conn.close()
                return True
        if identified_columns is not None:    
            if not table_exists:
                # 表不存在，创建表
                df.to_sql(table_name, conn, if_exists=if_exists, index=index)
                conn.close()
                return True
            if not use_temp_table:
                #  # 检查数据是否已存在于表中
                # 构建需要选择的字段            
                select_columns = ",".join(identified_columns)
                existing_data_query = f"SELECT {select_columns} FROM {table_name} WHERE " + " AND ".join([f"{col} = ?" for col in identified_columns])
                not_existing_data = []
                for index, row in df.iterrows():                
                    cursor.execute(existing_data_query,  [row[col] for col in identified_columns])
                    result = cursor.fetchall()
                    if len(result) == 0:
                        not_existing_data.append(row)            
                # 插入不存在的数据
                if not_existing_data:
                    new_data_df = pd.DataFrame(not_existing_data)
                    new_data_df.to_sql(f'{table_name}', conn, if_exists=if_exists, index=index)
                    logger.info("插入数据成功！")
                else:
                    logger.info("所有数据已存在，无需插入。")
            else:# 对于数据量较大的表，使用临时表：将要插入的数据存储在临时表中，然后执行一次查询来过滤出已存在的数据，最后将剩余的数据插入到目标表中。                
                # 按批次插入数据
                for i in tqdm(range(0, len(df), batch_size),leave=False,desc= "分批插入数据"):
                    batch_data_df = df[i:i+batch_size]
                    insert_unique_data(conn, batch_data_df, table_name, identified_columns)
                if len(df) > 100000:#数据条数超过十万，需要 VACUUM 命令来重建数据库文件，并清除未使用的空间，从而减小数据库文件的大小
                    logger.info(f"start to VACUUM {str_sqlite_db}")#cursor.rowcount获取生效的条数  
                    # 执行 VACUUM 命令
                    cursor.execute("VACUUM")
                    # 提交更改
                    conn.commit()
            conn.close()
        else:
            # 建立与SQLite数据库的连接
            engine = create_engine(f'sqlite:///{str_sqlite_db}')  # 这里的"data.db"是SQLite数据库文件的路径
            # 将DataFrame数据插入数据库表
            df.to_sql(table_name, con = engine.connect(), if_exists=if_exists, index=index)   
            # 关闭数据库连接
            engine.dispose()
        logger.info(f"save {table_name} to db done") 
        return True 
    except Exception as e:
            logger.error(f"save {table_name} to db failed", e)     
            return False  
        
def rebulid_db(str_sqlite_db):
    '''
    @description: 重建数据库
    @param {str} str_sqlite_db: SQLite数据库文件路径
    '''
    conn = sqlite3.connect(f"{str_sqlite_db}") 
    cursor = conn.cursor()
    logger.info(f"start to VACUUM {str_sqlite_db}") 
    # 执行 VACUUM 命令
    cursor.execute("VACUUM")
    # 提交更改
    conn.commit()
    conn.close()           
                  
def insert_unique_data(conn, df, table_name, unique_columns):
    '''
    @description: 插入唯一数据:使用临时表：将要插入的数据存储在临时表中，然后执行一次查询来过滤出已存在的数据，最后将剩余的数据插入到目标表中。
    @param {sqlite3.Connection} conn: 数据库连接
    @param {pd.DataFrame} df: 数据框
    @param {str} table_name: 表名
    @param {list} unique_columns: 唯一列名列表
    '''
    try:
        letters = string.ascii_letters
        random_name=''.join(random.choice(letters) for _ in range(8)) 
        # 创建临时表    
        temp_table_name = f'{table_name}_{random_name}'        
        # 创建临时表并将数据插入临时表
        df.to_sql(temp_table_name, conn, if_exists='replace', index=False)
        # 构建唯一记录字段的查询条件
        unique_conditions = " AND ".join([f"{table_name}.{col} = {temp_table_name}.{col}" for col in unique_columns])
        # 使用一次查询来检查并插入数据
        # query = f"""
        # INSERT INTO {table_name}
        # SELECT *
        # FROM {temp_table_name}
        # WHERE NOT EXISTS (
        #     SELECT 1
        #     FROM {table_name}
        #     WHERE {unique_conditions}
        # )
        # """      
        # 改用left join提高sql执行效率
        condition_field = f't2.{unique_columns[0]} IS NULL'
        join_conditions = ' AND '.join([f't1.{col} = t2.{col}' for col in unique_columns])
        query = f''' 
                    INSERT INTO {table_name}                   
                    SELECT t1.* FROM {temp_table_name} t1
                    LEFT JOIN {table_name} t2 ON {join_conditions}
                    WHERE {condition_field}
                    '''
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()  
        logger.info(f"insert {cursor.rowcount} records to {table_name} done")#cursor.rowcount获取生效的条数        
        # 删除临时表
        conn.execute(f"DROP TABLE {temp_table_name}")
        # if len(df) > 10000:#数据条数超过一万，需要 VACUUM 命令来重建数据库文件，并清除未使用的空间，从而减小数据库文件的大小
        #     logger.info(f"start to VACUUM {str_sqlite_db}")#cursor.rowcount获取生效的条数  
        #     # 执行 VACUUM 命令
        #     cursor.execute("VACUUM")
        #     # 提交更改
        #     conn.commit()
        return True
    except Exception as e:
            logger.error(f"insert unique data to {table_name} failed", e)     
            return False  
    
def append_df_to_db(str_sqlite_db,df,table_name):
    '''
    @description: 将数据框追加到数据库
    @param {str} str_sqlite_db: SQLite数据库文件路径
    @param {pd.DataFrame} df: 数据框
    @param {str} table_name: 表名
    @return {bool} 成功返回True，失败返回False
    '''
    try:  
        # 连接到 SQLite 数据库
        conn = sqlite3.connect(str_sqlite_db)    
        # 将 DataFrame 中的数据追加到 SQLite 数据库表中
        df.to_sql(table_name, conn, if_exists='append', index=False)
        conn.commit()
        # 关闭数据库连接
        conn.close() 
        return True
    except Exception as e:
            logger.error(f"append {table_name} to db failed", e)     
            return False    
    
def query_db(str_sqlite_db,sql):
    '''
    @description: 查询数据库
    @param {str} str_sqlite_db: SQLite数据库文件路径
    @param {str} sql: SQL语句
    @return {pd.DataFrame} 查询结果数据框;  查询失败返回空数据框 
    '''
    try:    
        # 建立与SQLite数据库的连接
        engine = create_engine(f'sqlite:///{str_sqlite_db}')  # 这里的"data.db"是SQLite数据库文件的路径
         # 读取数据库表
        con = engine.connect()  # 获取数据库连接对象
        df = pd.read_sql(text(sql), con=con)  # 使用连接对象执行查询操作 #需要用sqlalchemy.text(sql)转为sql对象,否则ObjectNotExecutableError reading from
        # 读取数据库表
        #df = pd.read_sql(sql, engine)    
        # 关闭数据库连接
        engine.dispose()
        return df
    except Exception as e:
        logger.error(f"failed to query {str_sqlite_db} with {sql}", e)     
        return pd.DataFrame()       
