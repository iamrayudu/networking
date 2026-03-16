import time
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

_log = logging.getLogger('chrome_guards')


def guard_page_loaded(driver, expected_url_fragment=None, timeout=8):
    """Returns {"ok": bool, "reason": str}"""
    try:
        current_url = driver.current_url
    except Exception:
        _log.warning('guard_page_loaded: could not read current_url — page_not_ready')
        return {"ok": False, "reason": "page_not_ready"}

    # Check 1: login redirect
    if "linkedin.com/login" in current_url or "linkedin.com/authwall" in current_url:
        _log.warning(f'guard_page_loaded: FAILED — redirected_to_login (url={current_url})')
        return {"ok": False, "reason": "redirected_to_login"}

    # Check 2: expected URL fragment
    if expected_url_fragment and expected_url_fragment not in current_url:
        _log.warning(f'guard_page_loaded: FAILED — wrong_page expected={expected_url_fragment} got={current_url}')
        return {"ok": False, "reason": "wrong_page"}

    # Check 3: document ready
    try:
        ready = False
        deadline = time.time() + timeout
        while time.time() < deadline:
            state = driver.execute_script("return document.readyState")
            if state == "complete":
                ready = True
                break
            time.sleep(0.5)
        if not ready:
            _log.warning(f'guard_page_loaded: FAILED — page_not_ready after {timeout}s (url={current_url})')
            return {"ok": False, "reason": "page_not_ready"}
    except Exception:
        return {"ok": False, "reason": "page_not_ready"}

    # Check 4: CAPTCHA
    try:
        page_source = driver.page_source
        if ("captcha-challenge" in page_source or
                "Let's do a quick security check" in page_source or
                "security verification" in page_source.lower()):
            _log.error(f'guard_page_loaded: FAILED — captcha_detected (url={current_url})')
            return {"ok": False, "reason": "captcha_detected"}
    except Exception:
        pass

    # Check 5: Profile not found
    try:
        page_source = driver.page_source
        if ("Page not found" in page_source or
                "This profile is no longer available" in page_source or
                "profile isn't available" in page_source.lower()):
            _log.info(f'guard_page_loaded: FAILED — profile_not_found (url={current_url})')
            return {"ok": False, "reason": "profile_not_found"}
    except Exception:
        pass

    _log.debug(f'guard_page_loaded: PASSED (url={current_url})')
    return {"ok": True, "reason": "ok"}


def guard_search_has_results(driver):
    """Returns {"ok": bool, "count": int, "reason": str}"""
    try:
        # Check 1: no results text
        try:
            page_source = driver.page_source
            if "No results found" in page_source:
                return {"ok": False, "count": 0, "reason": "zero_results"}
        except Exception:
            pass

        # Check 2: find profile cards — try multiple selectors (LinkedIn changes DOM frequently)
        card_selectors = [
            ".entity-result__title-text",           # classic
            ".reusable-search__result-container",   # newer layout
            "li.reusable-search__result-container", # list items
            "[data-chameleon-result-urn]",           # data attribute (robust)
            ".search-result__info",                  # fallback
        ]
        cards = []
        for sel in card_selectors:
            cards = driver.find_elements(By.CSS_SELECTOR, sel)
            if cards:
                _log.info(f'guard_search_has_results: found {len(cards)} cards via selector "{sel}"')
                break

        if not cards:
            # Last resort: check if any result list exists at all
            list_items = driver.find_elements(By.CSS_SELECTOR, "ul.reusable-search__entity-result-list li")
            if list_items:
                _log.info(f'guard_search_has_results: found {len(list_items)} list items as fallback')
                return {"ok": True, "count": len(list_items), "reason": "ok"}
            _log.warning('guard_search_has_results: FAILED — no profile cards found with any selector')
            return {"ok": False, "count": 0, "reason": "no_results_container"}

        count = len(cards)
        _log.info(f'guard_search_has_results: PASSED — {count} profile cards found')
        return {"ok": True, "count": count, "reason": "ok"}
    except Exception as e:
        _log.warning(f'guard_search_has_results: FAILED — exception: {e}')
        return {"ok": False, "count": 0, "reason": "no_results_container"}


def guard_profile_is_readable(driver):
    """Returns {"ok": bool, "reason": str, "quality": str}"""
    # First run page loaded check
    page_check = guard_page_loaded(driver)
    if not page_check["ok"]:
        return {"ok": False, "reason": page_check["reason"], "quality": "empty"}

    # Check 2: name element exists
    try:
        name_elements = driver.find_elements(By.CSS_SELECTOR, "h1.text-heading-xlarge")
        if not name_elements:
            return {"ok": False, "reason": "no_name_element", "quality": "empty"}
        name_text = name_elements[0].text.strip()
    except Exception:
        return {"ok": False, "reason": "no_name_element", "quality": "empty"}

    # Check 3: private profile
    if "LinkedIn Member" in name_text:
        return {"ok": False, "reason": "private_profile", "quality": "private"}

    # Check 4: content richness score
    score = 0
    has_about = False
    has_experience = False
    has_headline = False

    try:
        headline_els = driver.find_elements(By.CSS_SELECTOR, ".text-body-medium.break-words")
        if headline_els and headline_els[0].text.strip():
            has_headline = True
            score += 1
    except Exception:
        pass

    try:
        about_els = driver.find_elements(By.CSS_SELECTOR, "#about ~ .pvs-list__outer-container")
        if about_els:
            has_about = True
            score += 1
    except Exception:
        pass

    try:
        exp_els = driver.find_elements(By.CSS_SELECTOR, "#experience ~ .pvs-list__outer-container")
        if exp_els:
            has_experience = True
            score += 1
    except Exception:
        pass

    if score == 0:
        _log.info(f'guard_profile_is_readable: FAILED — profile_too_sparse (name={name_text!r}, headline={has_headline}, about={has_about}, exp={has_experience})')
        return {"ok": False, "reason": "profile_too_sparse", "quality": "empty"}

    quality = "good" if score >= 2 else "minimal"
    _log.info(f'guard_profile_is_readable: PASSED — quality={quality} score={score}/3 name={name_text!r}')
    return {"ok": True, "reason": "ok", "quality": quality}


def guard_connect_button_available(driver):
    """Returns {"ok": bool, "reason": str, "button_type": str}"""
    # Check 1: page loaded
    page_check = guard_page_loaded(driver, "linkedin.com/in/")
    if not page_check["ok"]:
        return {"ok": False, "reason": page_check["reason"], "button_type": "none"}

    # Check 2: direct Connect button
    try:
        connect_btns = driver.find_elements(
            By.XPATH, "//button[contains(@aria-label, 'Connect')]"
        )
        if connect_btns:
            return {"ok": True, "reason": "ok", "button_type": "direct"}
    except Exception:
        pass

    # Check 3: More menu
    try:
        more_btns = driver.find_elements(
            By.XPATH, "//button[contains(@aria-label, 'More actions')]"
        )
        if more_btns:
            more_btns[0].click()
            time.sleep(1)
            dropdown_connects = driver.find_elements(
                By.XPATH, "//span[text()='Connect']/ancestor::div[@role='option']"
            )
            if dropdown_connects:
                return {"ok": True, "reason": "ok", "button_type": "in_more_menu"}
    except Exception:
        pass

    # Check 4: Already connected
    try:
        page_source = driver.page_source
        if "Message" in page_source and "Following" in page_source:
            return {"ok": False, "reason": "already_connected", "button_type": "none"}
    except Exception:
        pass

    # Check 5: Pending
    try:
        pending_btns = driver.find_elements(
            By.XPATH, "//button[contains(@aria-label, 'Pending')]"
        )
        if pending_btns:
            return {"ok": False, "reason": "invitation_pending", "button_type": "none"}
    except Exception:
        pass

    return {"ok": False, "reason": "connect_unavailable", "button_type": "none"}


def guard_message_box_open(driver):
    """Returns {"ok": bool, "reason": str}"""
    # Check 1: textarea visible
    try:
        textareas = driver.find_elements(
            By.XPATH, "//textarea[contains(@placeholder, 'Add a note') or contains(@placeholder, 'note')]"
        )
        if textareas and textareas[0].is_displayed():
            # Check it's empty
            if textareas[0].get_attribute('value') == '':
                return {"ok": True, "reason": "ok"}
            else:
                return {"ok": False, "reason": "textarea_not_empty"}
    except Exception:
        pass

    # Check 2: try clicking "Add a note" button
    try:
        add_note_btns = driver.find_elements(
            By.XPATH, "//button[contains(@aria-label, 'Add a note')]"
        )
        if add_note_btns:
            add_note_btns[0].click()
            time.sleep(2)
            textareas = driver.find_elements(
                By.XPATH, "//textarea[contains(@placeholder, 'Add a note') or contains(@placeholder, 'note')]"
            )
            if textareas and textareas[0].is_displayed():
                return {"ok": True, "reason": "ok"}
    except Exception:
        pass

    return {"ok": False, "reason": "message_box_not_found"}
