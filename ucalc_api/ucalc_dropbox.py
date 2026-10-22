import os
from typing import Optional

import dropbox
from dropbox.exceptions import ApiError
from dropbox.files import WriteMode

_dbx: Optional[dropbox.Dropbox] = None


def get_client() -> dropbox.Dropbox:
    global _dbx
    if _dbx is None:
        token = os.getenv("UCALC_DROPBOX_TOKEN", "").strip()
        if not token:
            raise RuntimeError("UCALC_DROPBOX_TOKEN is not set")
        _dbx = dropbox.Dropbox(token)
    return _dbx


def get_user_info() -> dict:
    acc = get_client().users_get_current_account()
    return {
        "account_id": acc.account_id,
        "name": acc.name.display_name,
        "email": acc.email,
    }


def get_space_usage() -> dict:
    usage = get_client().users_get_space_usage()
    allocated = getattr(usage, "allocation", None)
    allocated_bytes = 0
    if allocated is not None:
        allocated_bytes = getattr(allocated, "allocated", 0) or 0
    return {
        "used": usage.used,
        "allocated": allocated_bytes,
    }


def list_folder(path: str = "") -> dict:
    try:
        res = get_client().files_list_folder(path)
    except ApiError as e:
        return {"error": str(e), "entries": []}
    entries = [
        {
            "name": e.name,
            "path": getattr(e, "path_display", getattr(e, "path_lower", "")),
            "type": type(e).__name__,
        }
        for e in res.entries
    ]
    return {"entries": entries}


def upload_file(local_bytes: bytes, remote_path: str) -> dict:
    """remote_path: e.g. '/ucalc_exports/history.json'"""
    result = get_client().files_upload(
        local_bytes, remote_path, mode=WriteMode("overwrite")
    )
    meta = getattr(result, "metadata", result)
    return {
        "name": getattr(meta, "name", remote_path.split("/")[-1]),
        "path": getattr(meta, "path_display", remote_path),
        "size": getattr(meta, "size", len(local_bytes)),
    }


def ensure_folder(path: str) -> None:
    try:
        get_client().files_create_folder_v2(path)
    except ApiError:
        # папка уже есть — ок
        pass


def create_shared_link(path: str) -> dict:
    try:
        links = get_client().sharing_list_shared_links(path=path, direct_only=True)
        if links.links:
            return {"url": links.links[0].url, "path": path}
    except ApiError:
        pass
    res = get_client().sharing_create_shared_link_with_settings(path)
    return {"url": res.url, "path": path}