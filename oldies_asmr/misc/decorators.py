from functools import wraps
from .utils import get_env_str


def only_on_env(env_list):
    """
    Decorator for functions to only run on certain envs, like "production_api"
    """

    def decorator(func):
        @wraps(func)
        def _wrapped_view(*args, **kwargs):
            if get_env_str() in env_list:
                return func(*args, **kwargs)

        return _wrapped_view

    return decorator
