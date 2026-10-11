"""Application launcher functions for i3wm."""
from typing import Dict, List, Optional
from backend_adapter import I3Adapter

_adapter = I3Adapter()


def get_available_apps() -> List[str]:
    """Returns a list of all launchable application names."""
    return _adapter.list_app_names()


def launch(app_name: str, workspace: Optional[str | int] = None) -> Dict[str, str]:
    """Launches an application by name on an optional workspace."""
    return _adapter.launch_app(query=app_name, workspace=workspace)
