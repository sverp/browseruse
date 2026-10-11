#!/usr/bin/env python3
"""
i3wm Backend Adapter for Computer Use & Window Management.
Can be imported as a Python module or executed directly via CLI.
"""

from typing import List, Dict, Any, Optional
import os
import subprocess
import glob
import re
from i3ipc import Connection


class I3Adapter:
    def __init__(self):
        self.i3 = Connection()

    def list_windows(self) -> List[Dict[str, Any]]:
        """List all application windows with metadata."""
        tree = self.i3.get_tree()
        windows = []
        for node in tree.leaves():
            if node.window and node.window_class != "i3bar":
                ws = node.workspace()
                windows.append({
                    "id": node.id,
                    "window_xid": node.window,
                    "name": node.name or "",
                    "class": node.window_class or "",
                    "workspace": ws.name if ws else None,
                    "focused": bool(node.focused),
                    "rect": {
                        "x": node.rect.x,
                        "y": node.rect.y,
                        "width": node.rect.width,
                        "height": node.rect.height,
                    },
                })
        return windows

    def find_windows(self, query: str) -> List[Any]:
        """Find container nodes matching ID, class, or title (prefers class over title)."""
        tree = self.i3.get_tree()
        query_lower = query.lower()
        candidates = [n for n in tree.leaves() if n.window and n.window_class != "i3bar"]

        # 1. Exact container or X11 ID
        id_matches = [n for n in candidates if str(n.id) == query or str(n.window) == query]
        if id_matches:
            return id_matches

        # 2. Match application class (e.g. 'firefox', 'kitty', 'code')
        class_matches = [n for n in candidates if n.window_class and query_lower in n.window_class.lower()]
        if class_matches:
            return class_matches

        # 3. Fallback to title/name match
        return [n for n in candidates if n.name and query_lower in n.name.lower()]

    def get_focused(self) -> Optional[Any]:
        """Returns currently focused window container."""
        return self.i3.get_tree().find_focused()

    def move_window(
        self,
        query: Optional[str] = None,
        workspace: Optional[str | int] = None,
        direction: Optional[str] = None,
        use_focused: bool = False,
    ) -> List[str]:
        """Move a window (by match query or focused) to a workspace or direction."""
        targets = []
        if use_focused:
            focused = self.get_focused()
            if focused:
                targets.append(focused)
        elif query:
            targets = self.find_windows(query)

        if not targets:
            return ["No matching window found."]

        results = []
        for node in targets:
            desc = f"{node.window_class or 'window'} ({node.id})"
            if workspace is not None:
                self.i3.command(f'[con_id="{node.id}"] move container to workspace {workspace}')
                results.append(f"Moved {desc} -> Workspace {workspace}")
            if direction:
                self.i3.command(f'[con_id="{node.id}"] move {direction}')
                results.append(f"Moved {desc} -> {direction}")
        return results

    def focus_window(self, query: str) -> bool:
        """Focus the first matching window."""
        matches = self.find_windows(query)
        if matches:
            self.i3.command(f'[con_id="{matches[0].id}"] focus')
            return True
        return False

    def unfullscreen_all(self) -> int:
        """Exit fullscreen on any fullscreen containers."""
        fullscreen_nodes = self.i3.get_tree().find_fullscreen()
        for node in fullscreen_nodes:
            node.command("fullscreen toggle")
        return len(fullscreen_nodes)

    def switch_workspace(self, workspace: str | int) -> None:
        """Switch current view to workspace."""
        self.i3.command(f"workspace {workspace}")

    @staticmethod
    def draw_grid_overlay(image_path: str, step: int = 100) -> str:
        """Draws semi-transparent (x, y) coordinate lines and labels over the image."""
        from utils import add_coordinate_grid
        return add_coordinate_grid(image_path, step=step)

    def screenshot_window(
        self,
        query: Optional[str] = None,
        output_path: str = "screenshot.png",
        add_grid: bool = False,
        grid_step: int = 100,
    ) -> str:
        """Capture screenshot of a targeted window, or currently focused window if query is None."""
        if query:
            matches = self.find_windows(query)
            if not matches:
                raise RuntimeError(f"No window found matching '{query}'.")
            target = matches[0]
        else:
            target = self.get_focused()

        if not target:
            raise RuntimeError("No active window to capture.")

        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        saved = False
        # 1. Try ImageMagick import using X11 window ID
        if target.window:
            res = subprocess.run(["import", "-window", str(target.window), output_path], capture_output=True)
            if res.returncode == 0 and os.path.exists(output_path):
                saved = True

        # 2. Fallback to PIL ImageGrab with window bounding box
        if not saved:
            try:
                from PIL import ImageGrab
                bbox = (
                    target.rect.x,
                    target.rect.y,
                    target.rect.x + target.rect.width,
                    target.rect.y + target.rect.height,
                )
                img = ImageGrab.grab(bbox=bbox)
                img.save(output_path)
                saved = True
            except Exception as e:
                raise RuntimeError(f"Failed to capture screenshot: {e}")

        if add_grid:
            self.draw_grid_overlay(output_path, step=grid_step)

        return output_path

    def screenshot_focused(
        self,
        output_path: str = "screenshot.png",
        add_grid: bool = False,
        grid_step: int = 100,
    ) -> str:
        """Capture screenshot of currently focused window, optionally with (x, y) grid overlay."""
        return self.screenshot_window(query=None, output_path=output_path, add_grid=add_grid, grid_step=grid_step)

    def list_installed_apps(self) -> List[Dict[str, str]]:
        """List all discoverable installed GUI applications from .desktop files."""
        desktop_dirs = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            os.path.expanduser("~/.local/share/applications"),
            "/var/lib/flatpak/exports/share/applications",
            os.path.expanduser("~/.local/share/flatpak/exports/share/applications"),
        ]

        apps: Dict[str, Dict[str, str]] = {}
        for d in desktop_dirs:
            if not os.path.isdir(d):
                continue
            for f in glob.glob(os.path.join(d, "*.desktop")):
                name, exec_cmd, nodisplay = None, None, False
                try:
                    with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                        in_entry = False
                        for line in fp:
                            line = line.strip()
                            if line == "[Desktop Entry]":
                                in_entry = True
                            elif line.startswith("[") and in_entry:
                                in_entry = False
                            if in_entry:
                                if line.startswith("Name=") and not name:
                                    name = line.split("=", 1)[1]
                                elif line.startswith("Exec=") and not exec_cmd:
                                    exec_cmd = line.split("=", 1)[1]
                                elif line.startswith("NoDisplay="):
                                    nodisplay = line.split("=", 1)[1].lower() == "true"
                    if name and exec_cmd and not nodisplay:
                        clean_cmd = re.sub(r"%[a-zA-Z]", "", exec_cmd).strip()
                        key = name.lower()
                        if key not in apps:
                            apps[key] = {"name": name, "exec": clean_cmd, "file": f}
                except Exception:
                    continue

        return sorted(apps.values(), key=lambda a: a["name"].lower())

    def list_app_names(self) -> List[str]:
        """Returns only the names of installed applications."""
        return [app["name"] for app in self.list_installed_apps()]

    def launch_app(self, query: str, workspace: Optional[str | int] = None) -> Dict[str, str]:
        """Launch an application matching name or command, optionally on a workspace."""
        apps = self.list_installed_apps()
        query_lower = query.lower()

        match = None
        for a in apps:
            if a["name"].lower() == query_lower:
                match = a
                break

        if not match:
            for a in apps:
                if query_lower in a["name"].lower() or query_lower in a["exec"].lower():
                    match = a
                    break

        app_name = match["name"] if match else query
        cmd = match["exec"] if match else query

        if workspace is not None:
            self.switch_workspace(workspace)

        self.i3.command(f"exec --no-startup-id {cmd}")
        return {"name": app_name, "exec": cmd}
