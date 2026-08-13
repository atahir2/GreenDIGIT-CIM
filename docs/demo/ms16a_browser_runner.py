"""MS16A one-off Chrome validation runner (not a CIM architecture change).

Uses the locally installed Google Chrome channel via Playwright.
Does not modify sample_data. Session-only Playwright package required:

    .venv\\Scripts\\python.exe -m pip install playwright
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DIR = ROOT / "sample_data"
SCREEN_DIR = ROOT / "docs" / "demo" / "screenshots" / "ms16a"
LOG_DIR = ROOT / "docs" / "demo" / "logs" / "ms16a"
RESULTS_PATH = LOG_DIR / "browser_run_results.json"

UPLOADER_URL = "http://127.0.0.1:8501"
ADMIN_URL = "http://127.0.0.1:8502"
API_DOCS_URL = "http://127.0.0.1:8000/docs"
API_HEALTH_URL = "http://127.0.0.1:8000/health"

# sample_data files in a stable, scenario-oriented order
SAMPLE_FILES = [
    ("datacenter_A.json", "A_known_operational+D_facility_kpi"),
    ("datacenter_B.xml", "A_known_operational"),
    ("datacenter_C.csv", "A_known_operational"),
    ("datacenter_D.yaml", "A_known_operational"),
    ("datacenter_Z.json", "A_known_operational_partial"),
    ("payload_cloud.json", "C_workflow+D_facility_kpi"),
    ("payload_grid.json", "C_workflow+D_facility_kpi"),
    ("payload_network.json", "C_workflow+network"),
    ("ifca.json", "C_workflow"),
    ("unstructured_dc_1.txt", "A_known_operational_unstructured"),
    ("unstructured_dc_2.txt", "A_known_operational_unstructured"),
]

ADMIN_PAGES = [
    "Unknown metrics (legacy)",
    "Registry browser",
    "Candidate review",
    "Evidence readiness",
    "KPI calculation",
    "Provenance timeline",
]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _shot(page, name: str) -> str:
    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREEN_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _visible_text(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=5000)
    except Exception:
        return ""


def _console_bucket():
    return {"errors": [], "warnings": [], "logs": []}


def attach_console(page, bucket: dict) -> None:
    def _on_msg(msg):
        rec = {"type": msg.type, "text": msg.text}
        if msg.type == "error":
            bucket["errors"].append(rec)
        elif msg.type == "warning":
            bucket["warnings"].append(rec)
        else:
            bucket["logs"].append(rec)

    page.on("console", _on_msg)
    page.on("pageerror", lambda exc: bucket["errors"].append({"type": "pageerror", "text": str(exc)}))


def wait_streamlit_ready(page, timeout_ms: int = 30000) -> None:
    page.wait_for_selector("h1, [data-testid='stApp']", timeout=timeout_ms)
    # Streamlit running spinner
    try:
        page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=8000)
    except PlaywrightTimeout:
        pass


def upload_and_ingest(page, file_path: Path) -> dict:
    result = {
        "file": file_path.name,
        "accepted": False,
        "ingest_clicked": False,
        "success": False,
        "error": None,
        "page_text": "",
        "screenshot": None,
        "elapsed_s": None,
    }
    started = time.time()
    page.goto(UPLOADER_URL, wait_until="domcontentloaded", timeout=60000)
    wait_streamlit_ready(page)

    file_input = page.locator("input[type='file']")
    file_input.wait_for(state="attached", timeout=15000)
    file_input.set_input_files(str(file_path))
    result["accepted"] = True

    # File selection triggers a Streamlit rerun; Ingest appears after that.
    ingest = page.get_by_role("button", name="Ingest")
    ingest.wait_for(state="visible", timeout=30000)
    ingest.click()
    result["ingest_clicked"] = True

    # Wait for success or error (Influx or parser)
    deadline = time.time() + 90
    last_text = ""
    while time.time() < deadline:
        try:
            page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=2000)
        except PlaywrightTimeout:
            pass
        last_text = _visible_text(page)
        if "Ingestion complete" in last_text or "Ingestion failed" in last_text or "No numeric metrics" in last_text:
            break
        time.sleep(0.6)

    result["page_text"] = last_text
    result["success"] = "Ingestion complete" in last_text
    if "Ingestion failed" in last_text:
        m = re.search(r"Ingestion failed:.*", last_text)
        result["error"] = m.group(0) if m else "Ingestion failed"
    elif "No numeric metrics" in last_text:
        result["error"] = "No numeric metrics detected"
    result["elapsed_s"] = round(time.time() - started, 2)
    result["screenshot"] = _shot(page, f"uploader_{_slug(file_path.name)}")
    return result


def click_admin_section(page, label: str) -> None:
    sidebar = page.locator("[data-testid='stSidebar']")
    sidebar.get_by_text(label, exact=True).first.click()
    time.sleep(1.2)
    wait_streamlit_ready(page)


def main() -> int:
    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "urls": {
            "uploader": UPLOADER_URL,
            "admin": ADMIN_URL,
            "api_docs": API_DOCS_URL,
            "api_health": API_HEALTH_URL,
        },
        "sample_dir": str(SAMPLE_DIR),
        "health": {},
        "landing": {},
        "uploads": [],
        "admin": [],
        "console": {},
        "ended_at": None,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=False,
            args=["--start-maximized", "--disable-backgrounding-occluded-windows"],
        )
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()
        console = _console_bucket()
        attach_console(page, console)

        # --- health + docs ---
        page.goto(API_HEALTH_URL, wait_until="domcontentloaded", timeout=30000)
        run["health"]["body"] = _visible_text(page)
        run["health"]["screenshot"] = _shot(page, "00_api_health")

        page.goto(API_DOCS_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        run["landing"]["api_docs_screenshot"] = _shot(page, "01_api_docs")

        # --- uploader landing ---
        page.goto(UPLOADER_URL, wait_until="domcontentloaded", timeout=60000)
        wait_streamlit_ready(page)
        page.get_by_text("Ingestion Uploader").first.wait_for(timeout=30000)
        page.wait_for_timeout(1500)
        run["landing"]["uploader_text"] = _visible_text(page)
        run["landing"]["uploader_screenshot"] = _shot(page, "02_uploader_landing")

        # --- each sample file ---
        for fname, scenario in SAMPLE_FILES:
            path = SAMPLE_DIR / fname
            rec = {"scenario_tag": scenario, "exists": path.exists()}
            if not path.exists():
                rec["error"] = "file missing"
                run["uploads"].append(rec)
                continue
            try:
                rec.update(upload_and_ingest(page, path))
            except Exception as exc:
                rec["error"] = f"{type(exc).__name__}: {exc}"
                rec["screenshot"] = _shot(page, f"uploader_{_slug(fname)}_exception")
                rec["page_text"] = _visible_text(page)
            run["uploads"].append(rec)

        # --- admin portal sections (result visibility, not full MS16B) ---
        page.goto(ADMIN_URL, wait_until="domcontentloaded", timeout=60000)
        wait_streamlit_ready(page)
        page.get_by_text("CIM Admin Portal").first.wait_for(timeout=30000)
        page.wait_for_timeout(1500)
        run["admin"].append(
            {
                "section": "landing",
                "text": _visible_text(page)[:4000],
                "screenshot": _shot(page, "90_admin_landing"),
            }
        )
        for label in ADMIN_PAGES:
            try:
                click_admin_section(page, label)
                text = _visible_text(page)
                run["admin"].append(
                    {
                        "section": label,
                        "text": text[:4000],
                        "screenshot": _shot(page, f"91_admin_{_slug(label)}"),
                        "error": None,
                    }
                )
            except Exception as exc:
                run["admin"].append(
                    {
                        "section": label,
                        "error": f"{type(exc).__name__}: {exc}",
                        "text": _visible_text(page)[:2000],
                        "screenshot": _shot(page, f"91_admin_{_slug(label)}_error"),
                    }
                )

        run["console"] = {
            "errors": console["errors"][:50],
            "warnings": console["warnings"][:50],
            "error_count": len(console["errors"]),
            "warning_count": len(console["warnings"]),
        }
        run["ended_at"] = datetime.now(timezone.utc).isoformat()
        RESULTS_PATH.write_text(json.dumps(run, indent=2), encoding="utf-8")
        context.close()
        browser.close()

    print(f"Wrote {RESULTS_PATH}")
    print(f"Screenshots: {SCREEN_DIR}")
    ok = sum(1 for u in run["uploads"] if u.get("success"))
    print(f"Uploader successes: {ok}/{len(run['uploads'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
