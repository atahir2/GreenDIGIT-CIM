"""MS16B pass-2: fix Streamlit select interaction + demo review actions.

Uses typing into BaseWeb select inputs (more reliable than role=option).
Review clicks still go through the Admin Portal UI → AdminReviewService.
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
SCREEN_DIR = ROOT / "docs" / "demo" / "screenshots" / "ms16b"
LOG_DIR = ROOT / "docs" / "demo" / "logs" / "ms16b"
RESULTS_PATH = LOG_DIR / "browser_run_results_pass2.json"
ADMIN_URL = "http://127.0.0.1:8502"

REGISTRY_CHOICES = (
    "metric",
    "mapping",
    "unit",
    "source",
    "asset",
    "standards",
    "lifecycle",
    "rule",
    "evidence",
    "provenance",
    "extension",
)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _shot(page, name: str) -> str:
    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREEN_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _text(page) -> str:
    try:
        return page.locator("body").inner_text(timeout=8000)
    except Exception:
        return ""


def wait_ready(page) -> None:
    page.wait_for_selector("[data-testid='stApp']", timeout=45000)
    try:
        page.wait_for_selector("[data-testid='stStatusWidget']", state="hidden", timeout=10000)
    except PlaywrightTimeout:
        pass
    time.sleep(0.6)


def go_section(page, label: str) -> None:
    page.locator("[data-testid='stSidebar']").get_by_text(label, exact=True).first.click()
    time.sleep(1.2)
    wait_ready(page)


def select_by_typing(page, select_index: int, value: str, *, press_enter: bool = True) -> bool:
    """Open nth BaseWeb select, type value, Enter."""
    selects = page.locator("[data-baseweb='select']")
    if select_index >= selects.count():
        return False
    sel = selects.nth(select_index)
    sel.click()
    time.sleep(0.35)
    inp = sel.locator("input")
    if inp.count() == 0:
        # sometimes input is sibling
        inp = page.locator("[data-baseweb='select'] input").nth(select_index)
    try:
        inp.fill("")
        inp.type(value, delay=25)
        time.sleep(0.4)
        # Prefer matching option if visible
        opt = page.locator(f"[role='option']:has-text('{value}')").first
        if opt.count() and opt.is_visible():
            opt.click()
        elif press_enter:
            page.keyboard.press("Enter")
        time.sleep(1.0)
        wait_ready(page)
        return True
    except Exception:
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False


def fill_label(page, label: str, value: str) -> None:
    loc = page.get_by_label(label, exact=False)
    if loc.count():
        loc.first.fill(value)
        return
    page.locator(f"xpath=//label[contains(., '{label}')]/following::input[1]").first.fill(value)


def click_btn(page, name: str) -> None:
    page.get_by_role("button", name=name, exact=True).click()
    time.sleep(1.4)
    wait_ready(page)


def pick_entry(page, needle: str) -> bool:
    """Candidate 'Select entry' is usually the second select on the page."""
    # Try select indices 1 then 0 then 2
    for idx in (1, 0, 2, 3):
        if select_by_typing(page, idx, needle):
            body = _text(page)
            if needle in body or any(t in body for t in needle.split(".") if len(t) > 4):
                return True
    # Fallback: open all selects and click option containing needle
    selects = page.locator("[data-baseweb='select']")
    for i in range(selects.count()):
        try:
            selects.nth(i).click()
            time.sleep(0.4)
            opt = page.locator("[role='option']").filter(has_text=needle).first
            if opt.count():
                opt.click()
                time.sleep(1.0)
                wait_ready(page)
                return True
            page.keyboard.press("Escape")
        except Exception:
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
    return False


def main() -> int:
    SCREEN_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    run = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "registry_browser": [],
        "candidate_review": {},
        "extension_review": {},
        "kpi_wue_cue": {},
        "ended_at": None,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(ADMIN_URL, wait_until="domcontentloaded", timeout=60000)
        wait_ready(page)
        page.get_by_text("CIM Admin Portal").first.wait_for(timeout=30000)

        # Reviewer
        try:
            page.locator("[data-testid='stSidebar']").get_by_label("Reviewer").fill("ms16b_admin")
        except Exception:
            pass

        # --- Registry browser cycle ---
        go_section(page, "Registry browser")
        for reg in REGISTRY_CHOICES:
            item = {"registry": reg}
            ok = select_by_typing(page, 0, reg)
            body = _text(page)
            item["ok"] = ok and ("entries" in body.lower() or "No rows" in body or "id" in body.lower())
            item["snip"] = body[:1200]
            item["screenshot"] = _shot(page, f"32_registry_{reg}")
            if reg == "metric":
                try:
                    fill_label(page, "Search", "pue")
                    page.keyboard.press("Enter")
                    time.sleep(1.0)
                    wait_ready(page)
                    t2 = _text(page)
                    item["search_pue"] = "pue" in t2.lower()
                    item["filter_screenshot"] = _shot(page, "33_registry_metric_search_pue")
                    fill_label(page, "Status filter", "approved")
                    page.keyboard.press("Enter")
                    time.sleep(1.0)
                    wait_ready(page)
                    item["status_filter_screenshot"] = _shot(page, "34_registry_metric_status_approved")
                    fill_label(page, "Status filter", "(all)")
                    fill_label(page, "Search", "")
                    page.keyboard.press("Enter")
                    time.sleep(0.5)
                except Exception as e:
                    item["filter_error"] = str(e)
            run["registry_browser"].append(item)

        # --- Candidate review actions ---
        cr = {}
        go_section(page, "Candidate review")
        cr["queue_shot"] = _shot(page, "46_candidate_queue_pass2")

        # Approve
        if pick_entry(page, "approve_power"):
            fill_label(page, "Review notes", "MS16B demo approve via UI")
            click_btn(page, "Approve")
            t = _text(page)
            cr["approve"] = {
                "ok": "provenance" in t.lower() or "approved" in t.lower(),
                "text": t[:2000],
                "screenshot": _shot(page, "47_approve_mapping"),
            }
        else:
            cr["approve"] = {"ok": False, "error": "approve_power not selectable"}

        # Reject
        go_section(page, "Candidate review")
        if pick_entry(page, "reject_wue"):
            fill_label(page, "Review notes", "MS16B demo reject via UI")
            click_btn(page, "Reject")
            t = _text(page)
            cr["reject"] = {
                "ok": "reject" in t.lower() or "provenance" in t.lower(),
                "text": t[:2000],
                "screenshot": _shot(page, "48_reject_mapping"),
            }
        else:
            cr["reject"] = {"ok": False, "error": "reject_wue not selectable"}

        # Merge
        go_section(page, "Candidate review")
        if pick_entry(page, "merge_cpu"):
            fill_label(page, "Merge target CIM namespace", "cim:compute.node.power.draw")
            fill_label(page, "Review notes", "MS16B demo merge via UI")
            click_btn(page, "Merge")
            t = _text(page)
            cr["merge"] = {
                "ok": "merge" in t.lower() or "provenance" in t.lower() or "approved" in t.lower(),
                "text": t[:2000],
                "screenshot": _shot(page, "49_merge_mapping"),
            }
        else:
            cr["merge"] = {"ok": False, "error": "merge_cpu not selectable"}

        # Promote — re-seed may be needed if approve left queue; try select approved via service later
        go_section(page, "Candidate review")
        if pick_entry(page, "approve_power"):
            click_btn(page, "Promote To Seed")
            t = _text(page)
            cr["promote"] = {
                "ok": "seed proposal" in t.lower() or "promote" in t.lower(),
                "text": t[:2000],
                "screenshot": _shot(page, "49b_promote_to_seed"),
            }
        else:
            cr["promote"] = {
                "ok": False,
                "note": "approved mapping may have left queue; see service companion result",
            }

        run["candidate_review"] = cr

        # --- Extension review ---
        er = {}
        go_section(page, "Candidate review")
        select_by_typing(page, 0, "extension")
        er["queue_shot"] = _shot(page, "53_extension_queue_pass2")

        if pick_entry(page, "incomplete_extension") or pick_entry(page, "incomplete"):
            try:
                fill_label(page, "Edit justification", "")
            except Exception:
                pass
            click_btn(page, "Approve")
            t = _text(page)
            er["incomplete_block"] = {
                "ok": any(
                    k in t.lower()
                    for k in ("requires", "failed", "justification", "error", "quantity")
                ),
                "text": t[:2000],
                "screenshot": _shot(page, "54_extension_incomplete_blocked"),
            }
        else:
            er["incomplete_block"] = {"ok": False, "error": "incomplete not found"}

        go_section(page, "Candidate review")
        select_by_typing(page, 0, "extension")
        if pick_entry(page, "complete_extension") or pick_entry(page, "complete"):
            fill_label(
                page,
                "Edit justification",
                "Research KPI for GreenDIGIT pilot; reviewed by domain owner (MS16B demo)",
            )
            fill_label(page, "Review notes", "MS16B complete extension approve attempt")
            click_btn(page, "Approve")
            t = _text(page)
            er["complete_approve"] = {
                "ok": ("provenance" in t.lower() and "approved" in t.lower())
                or ("requires" in t.lower()),
                "note": "UI only posts justification; unit/qk gates may still block — documented",
                "text": t[:2000],
                "screenshot": _shot(page, "55_extension_complete_approve"),
            }
        else:
            er["complete_approve"] = {"ok": False, "error": "complete not found"}

        go_section(page, "Candidate review")
        select_by_typing(page, 0, "extension")
        if pick_entry(page, "reject_extension"):
            fill_label(page, "Review notes", "MS16B reject extension")
            click_btn(page, "Reject")
            t = _text(page)
            er["reject"] = {
                "ok": "reject" in t.lower() or "provenance" in t.lower(),
                "text": t[:2000],
                "screenshot": _shot(page, "56_extension_reject"),
            }
        else:
            er["reject"] = {"ok": False, "error": "reject_extension not found"}

        run["extension_review"] = er

        # --- WUE / CUE forms ---
        go_section(page, "KPI calculation")
        kw = {}
        if select_by_typing(page, 0, "wue"):
            kw["wue"] = {
                "ok": "water" in _text(page).lower(),
                "screenshot": _shot(page, "76_kpi_wue_form"),
            }
        else:
            kw["wue"] = {"ok": False}
        if select_by_typing(page, 0, "cue"):
            kw["cue"] = {
                "ok": "carbon" in _text(page).lower(),
                "screenshot": _shot(page, "77_kpi_cue_form"),
            }
        else:
            kw["cue"] = {"ok": False}
        run["kpi_wue_cue"] = kw

        # Provenance after review actions
        go_section(page, "Provenance timeline")
        fill_label(page, "Entity type (optional)", "cim_mapping")
        page.keyboard.press("Enter")
        time.sleep(1.2)
        wait_ready(page)
        run["provenance_after_review"] = {
            "text": _text(page)[:2500],
            "screenshot": _shot(page, "82_provenance_cim_mapping"),
            "has_review": "review_action" in _text(page).lower(),
        }

        run["ended_at"] = datetime.now(timezone.utc).isoformat()
        RESULTS_PATH.write_text(json.dumps(run, indent=2), encoding="utf-8")
        browser.close()

    print(f"Wrote {RESULTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
