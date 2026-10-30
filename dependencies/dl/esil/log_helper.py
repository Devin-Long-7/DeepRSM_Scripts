import logging
from logging.handlers import TimedRotatingFileHandler
import os

# 配置日志记录器
def get_logger(log_file_name,identifier=None,when='midnight',interval=1,backupCount=0,suffix=None):
    '''
    @description: 获取日志记录器
    @param {str} log_file_name: 日志文件名，可以包含路径
    @param {str} identifier: 日志记录器的标识符，用于区分不同的日志记录器; 默认值为None，即使用调用者的文件名作为日志标识符   
    @param {str} when: 日志轮换频率，'S': 每秒, 'M': 每分钟,'H': 每小时,'D': 每天, 'W0' - 'W6': 每周的某一天（0为星期一，6为星期日）,'midnight': 每天午夜,默认值为midnight
    @param {int} interval: 日志轮换间隔，默认1
    @param {int} backupCount: 日志保留数量，默认0;保留的旧日志文件的数量，超过这个数量后会删除最旧的日志文件。
    @param {str} suffix: 日志文件后缀，默认值为None，即日期格式为"%Y-%m-%d_%H-%M-%S"
    @return: 日志记录器
    '''
    dir=os.path.dirname(log_file_name)
    if dir and not os.path.exists(dir):
        os.makedirs(dir)    
    if identifier is None:#使用调用者的文件名作为日志标识符 
        import inspect
        # 获取调用者的文件路径
        identifier =os.path.basename(inspect.stack()[1].filename).replace(".py","")    #inspect.stack()获取调用者的堆栈信息; 第二个元素是调用者的堆栈信息    
    logger = logging.getLogger(identifier)
    logger.setLevel(logging.INFO)    
    # 创建TimedRotatingFileHandler，每分钟生成一个带有日期时间戳的日志文件
    file_handler = logging.handlers.TimedRotatingFileHandler(log_file_name, when=when, interval=interval, backupCount=backupCount)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    if suffix is not None:
        file_handler.suffix = suffix
    logger.addHandler(file_handler)
    return logger

def write(e,currentFrame):
    # filename = sys._getframe().f_code.co_filename
    # function = sys._getframe().f_code.co_name
    # lineno = sys._getframe().f_lineno
    filename = currentFrame.f_code.co_filename
    function = currentFrame.f_code.co_name
    lineno = currentFrame.f_lineno
    exception = str(e)
    logErr(filename, function, lineno, exception)

def logErr(filename, function, lineno, e):
    import os   
    import time
    import logging
    current_path = os.path.abspath(__file__)
    parent_path = os.path.abspath(os.path.dirname(current_path) + os.path.sep + ".")
    today = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    logName = today + ".log"
    if not os.path.exists("{}/Log/".format(parent_path)):
        os.makedirs("{}/Log/".format(parent_path))
    # if not os.path.exists("{}/Log/{}/".format(parent_path, today)):
    #     os.makedirs("{}/Log/{}/".format(parent_path, today))
    # if not os.path.exists("{}/Log/{}/{}".format(parent_path, today, logName)):
    #     reportFile = open("{}/Log/{}/{}".format(parent_path, today, logName), 'w')
    if not os.path.exists("{}/Log/{}".format(parent_path, logName)):
        reportFile = open("{}/Log/{}".format(parent_path, logName), 'w')
        reportFile.close()
    logger = logging.getLogger()
    handler = logging.FileHandler("{}/Log/{}".format(parent_path, logName), encoding='utf8')
    console = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(filename)s %(funcName)s %(levelname)s %(message)s')
    print(str(formatter))

    handler.setFormatter(formatter)  # 将log信息绑定到log文件上
    console.setFormatter(formatter)  # 将log信息绑定到控制台输出窗口
    logger.addHandler(handler)
    logger.addHandler(console)
    logger.setLevel(logging.INFO)  # Set log print level(设置日志打印级别)
    logging.error(filename + '   Function: ' + function + '  Line: ' + str(lineno) + '  Exception: ' + e+"\n")
    # print(e,'log.py')
