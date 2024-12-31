class LiteBotyException(Exception):
    """基础异常类"""
    pass


class ServiceError(LiteBotyException):
    """服务相关错误"""
    pass


class ConfigError(LiteBotyException):
    """配置相关错误"""
    pass
