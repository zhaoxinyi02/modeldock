import json, urllib.request
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
    p1 = [int(x) for x in v1.split(".") if x.isdigit()]
    p2 = [int(x) for x in v2.split(".") if x.isdigit()]
    for a, b in zip(p1, p2):
        if a != b:
            return a - b
    return len(p1) - len(p2)
