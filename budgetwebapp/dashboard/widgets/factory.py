from core.logger import logger

def create_default_config(handler):
    """
    Builds default config using Pydantic schema defaults.
    """

    logger.warn(f'Creating default config for {handler.__name__}')

    schema = handler.CONFIG_SCHEMA

    if not schema:
        return {}

    # Pydantic v2: model_construct gives defaults without validation overhead
    return schema().model_dump()