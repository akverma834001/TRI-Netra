import numpy as np
from typing import Any

def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively converts NumPy scalars and ndarrays to native Python types
    to guarantee compatibility with FastAPI/Starlette JSON serialization.
    """
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(v) for v in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj
