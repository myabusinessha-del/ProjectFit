import os
import re


def _deployment_metadata():
    """Expose non-secret Render release identifiers for live verification."""
    metadata = {}
    revision = os.environ.get("RENDER_GIT_COMMIT", "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{7,40}", revision):
        metadata["revision"] = revision

    branch = os.environ.get("RENDER_GIT_BRANCH", "").strip()
    if branch and len(branch) <= 120:
        metadata["branch"] = branch

    service_name = os.environ.get("RENDER_SERVICE_NAME", "").strip()
    if service_name and len(service_name) <= 120:
        metadata["service_name"] = service_name

    return metadata


def health_status(database):
    """Return a lightweight readiness response without exposing internals."""
    deployment = _deployment_metadata()
    try:
        database.q("SELECT 1").fetchone()
    except Exception:
        payload = {
            "ok": False,
            "service": "ProjectFit",
            "database": "unavailable",
        }
        if deployment:
            payload["deployment"] = deployment
        return payload, 503

    payload = {
        "ok": True,
        "service": "ProjectFit",
        "database": "ok",
        "rule_version": "workbook_v1",
        "app_version": "2.2",
    }
    if deployment:
        payload["deployment"] = deployment
    return payload, 200
