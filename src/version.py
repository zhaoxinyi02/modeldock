import json, urllib.request
import re
from constants import *

def check_update():
    url = "https://api.github.com/repos/" + GITHUB_OWNER + "/" + GITHUB_REPO + "/releases/latest"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": APP_NAME})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        latest = data.get("tag_name", "").lstrip("Vv")
        current = APP_VERSION.lstrip("Vv")
        has_update = _compare_versions(latest, current) > 0
        return {
            "has_update": has_update,
            "latest_version": "V" + latest if latest else "",
            "current_version": APP_VERSION,
            "release_url": data.get("html_url", ""),
            "release_notes": (data.get("body", "") or "")[:500],
            "download_url": _get_download_url(data),
        }
    except Exception as e:
        return {
            "has_update": False,
            "error": str(e),
            "current_version": APP_VERSION,
        }

def _get_download_url(release_data):
    for asset in release_data.get("assets", []):
        name = asset.get("name", "")
        if name.endswith(".exe"):
            return asset.get("browser_download_url", "")
    return ""

def _compare_versions(v1, v2):
    p1, s1 = _parse_version(v1)
    p2, s2 = _parse_version(v2)
    for a, b in zip(p1, p2):
        if a != b:
            return a - b
    if len(p1) != len(p2):
        return len(p1) - len(p2)
    return s1 - s2


def _parse_version(v):
    m = re.match(r"(\d+)\.(\d+)\.(\d+)([a-z]?)", v or "", re.I)
    if not m:
        return [0, 0, 0], 0
    suffix = m.group(4).lower()
    return [int(m.group(1)), int(m.group(2)), int(m.group(3))], (ord(suffix) - 96 if suffix else 0)
