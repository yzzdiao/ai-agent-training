import logging


def get_logger(name: str) -> logging.Logger:
    # 集中创建 Logger，后续接入 JSON 日志/链路追踪时只改这里。
    logger = logging.getLogger(name)

    # 防止重复 import 导致重复输出日志。
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger
