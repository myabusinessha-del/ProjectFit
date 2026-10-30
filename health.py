def health_status(database):
    """Return a lightweight readiness response without exposing internals."""
    try:
        database.q("SELECT 1").fetchone()
    except Exception:
        return {
            "ok": False,
            "service": "ProjectFit",
            "database": "unavailable",
        }, 503

    return {
        "ok": True,
        "service": "ProjectFit",
        "database": "ok",
        "rule_version": "workbook_v1",
        "app_version": "2.2",
    }, 200
