class AppError(Exception):
    # 所有应用层异常的父类。
    pass


class LLMError(AppError):
    # LLM 相关异常的父类。
    pass


class LLMConfigError(LLMError):
    # API Key、模型名等配置错误。
    pass
