from pathlib import Path


def get_project_root() -> Path:
    """
    Get /hope path
    """
    return Path(__file__).parent
