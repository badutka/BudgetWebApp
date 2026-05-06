from budgetwebapp.dashboard.core.registry import get_widget_handler
from core.logger import logger

def create_default_config(widget_type: str, subtype: str):
    """
    Builds default config using Pydantic schema defaults.
    """

    handler_cls = get_widget_handler(widget_type, subtype)
    logger.warn(f'running create_default_config for {widget_type}:{subtype}')
    if not handler_cls:
        raise ValueError(f"No handler for {widget_type}:{subtype}")

    schema = handler_cls.CONFIG_SCHEMA
    logger.warn(f'{schema = }')
    if not schema:
        return {}

    # Pydantic v2: model_construct gives defaults without validation overhead
    return schema().model_dump()