import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit.components.v1 as components


_THIS_DIR = Path(__file__).resolve().parent
_TEMPLATE_PATH = _THIS_DIR / "frontend" / "index.html"
_TEMPLATE_HTML = _TEMPLATE_PATH.read_text(encoding="utf-8")


def ceph_component(
    *,
    image_data_url: str,
    marker_size: int,
    show_labels: bool,
    points: List[Dict[str, Any]],
    planes: List[Dict[str, Any]],
    angles: List[Dict[str, Any]],
    polygons: List[Dict[str, Any]],
    key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Render the custom cephalometric component."""
    payload: Dict[str, Any] = {
        "image_data_url": image_data_url,
        "marker_size": marker_size,
        "show_labels": show_labels,
        "points": points,
        "planes": planes,
        "angles": angles,
        "polygons": polygons,
        "key": key,
    }
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = _TEMPLATE_HTML.replace("__PAYLOAD_JSON__", payload_json)
    return components.html(html, height=820, scrolling=False)


__all__ = ["ceph_component"]
