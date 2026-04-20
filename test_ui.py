import re
from typing import Optional, Tuple

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "https://cerulean-praline-8e5aa6.netlify.app"
DESKTOP_VIEWPORT = {"width": 1280, "height": 800}
MOBILE_VIEWPORT  = {"width": 390,  "height": 844}


def goto_list(page: Page) -> None:
    page.goto(BASE_URL + "/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)


def goto_stats(page: Page) -> None:
    page.goto(BASE_URL + "/")
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
    page.locator("a[href='/stats']").click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)


def wait_for_list(page: Page) -> None:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1200)


def card_count(page: Page) -> int:
    return page.locator("[class*='card__title']").count()


def get_prices(page: Page) -> list[int]:
    prices = []
    for el in page.locator("[class*='card__price']").all():
        digits = re.sub(r"[^\d]", "", el.inner_text())
        if digits:
            prices.append(int(digits))
    return prices


def get_category_texts(page: Page) -> list[str]:
    return [el.inner_text().strip() for el in page.locator("[class*='card__category']").all()]


def get_priority_badges(page: Page) -> int:
    return page.locator("[class*='card__priority']").count()


def parse_stats_metrics(body_text: str) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    flat = body_text.replace("\n", " ")
    ma = re.search(r"ОДОБРЕНО\s*(\d+)\s*%", flat)
    mr = re.search(r"ОТКЛОНЕНО\s*(\d+)\s*%", flat)
    mt = re.search(r"СРЕДНЕЕ ВРЕМЯ\s*(\d+)", flat)
    ap = int(ma.group(1)) if ma else None
    rp = int(mr.group(1)) if mr else None
    avg = int(mt.group(1)) if mt else None
    return ap, rp, avg


def sidebar_category_select(page: Page):
    return page.locator("aside select").first


def sidebar_priority_select(page: Page):
    return page.locator("aside select").nth(1)


def search_by_title_input(page: Page):
    return page.locator('input[placeholder*="Введите название"]')


def sort_by_select(page: Page):
    return page.locator("[class*='filtersBar'] select").first


def sort_order_select(page: Page):
    return page.locator("[class*='filtersBar'] select").nth(1)


@pytest.fixture
def desktop_page(page: Page):
    page.set_viewport_size(DESKTOP_VIEWPORT)
    return page


@pytest.fixture
def mobile_page(page: Page):
    page.set_viewport_size(MOBILE_VIEWPORT)
    return page


class TestPriceRangeFilter:

    def test_price_filter_section_visible(self, desktop_page: Page):
        goto_list(desktop_page)
        expect(desktop_page.get_by_text("Диапазон цен (₽)")).to_be_visible()
        expect(desktop_page.get_by_placeholder("От")).to_be_visible()
        expect(desktop_page.get_by_placeholder("До")).to_be_visible()

    def test_max_price_reduces_card_count(self, desktop_page: Page):
        goto_list(desktop_page)
        initial = card_count(desktop_page)
        assert initial > 0

        prices = get_prices(desktop_page)
        assert prices
        mid = sorted(prices)[len(prices) // 2]

        desktop_page.get_by_placeholder("До").fill(str(mid))
        wait_for_list(desktop_page)

        assert card_count(desktop_page) <= initial

    def test_displayed_prices_respect_max_price(self, desktop_page: Page):
        goto_list(desktop_page)
        max_price = 10000
        desktop_page.get_by_placeholder("До").fill(str(max_price))
        wait_for_list(desktop_page)

        over = [p for p in get_prices(desktop_page) if p > max_price]
        assert not over, f"[BUG-UI-013] Cards with price > {max_price} still visible: {over}."

    def test_reset_clears_filters_ui_state(self, desktop_page: Page):
        goto_list(desktop_page)
        sidebar_category_select(desktop_page).select_option("5")
        desktop_page.get_by_placeholder("До").fill("99999")
        desktop_page.locator("label[class*='urgentToggle']").click()
        wait_for_list(desktop_page)

        desktop_page.locator("button[title='Сбросить все фильтры']").click()
        wait_for_list(desktop_page)
        wait_for_list(desktop_page)

        problems = []
        if sidebar_category_select(desktop_page).input_value() != "":
            problems.append("категория в сайдбаре не сброшена на «Все категории»")
        if desktop_page.get_by_placeholder("До").input_value() != "":
            problems.append("поле «До» не очищено")
        urgent = desktop_page.locator("label[class*='urgentToggle'] input[type='checkbox']")
        if urgent.is_checked():
            problems.append("тоггл «Только срочные» остаётся включённым")
        assert not problems, (
            "[BUG-UI-017] Кнопка «Сбросить все фильтры» не возвращает UI к начальному состоянию: "
            + "; ".join(problems)
        )

    def test_min_price_input_accepts_number(self, desktop_page: Page):
        goto_list(desktop_page)
        field = desktop_page.get_by_placeholder("От")
        field.fill("5000")
        assert field.input_value() == "5000"


class TestSortByPrice:

    def test_sort_ascending(self, desktop_page: Page):
        goto_list(desktop_page)
        sort_by_select(desktop_page).select_option("price")
        sort_order_select(desktop_page).select_option("asc")
        wait_for_list(desktop_page)

        prices = get_prices(desktop_page)
        assert len(prices) >= 2
        assert prices == sorted(prices), f"Not ascending: {prices}"

    def test_sort_descending(self, desktop_page: Page):
        goto_list(desktop_page)
        sort_by_select(desktop_page).select_option("price")
        sort_order_select(desktop_page).select_option("asc")
        wait_for_list(desktop_page)
        sort_order_select(desktop_page).select_option("desc")
        wait_for_list(desktop_page)

        prices = get_prices(desktop_page)
        assert len(prices) >= 2
        assert prices == sorted(prices, reverse=True), f"Not descending: {prices}"

    def test_switching_order_reorders_cards(self, desktop_page: Page):
        goto_list(desktop_page)
        sort_by_select(desktop_page).select_option("price")

        sort_order_select(desktop_page).select_option("asc")
        wait_for_list(desktop_page)
        prices_asc = get_prices(desktop_page)

        sort_order_select(desktop_page).select_option("desc")
        wait_for_list(desktop_page)
        prices_desc = get_prices(desktop_page)

        assert prices_asc != prices_desc


class TestCategoryFilter:

    def test_category_filter_shows_only_selected(self, desktop_page: Page):
        goto_list(desktop_page)
        sidebar_category_select(desktop_page).select_option("0")
        wait_for_list(desktop_page)

        cats = get_category_texts(desktop_page)
        assert cats
        assert all("Электроника" in c for c in cats), \
            f"Non-matching categories: {[c for c in cats if 'Электроника' not in c]}"

    def test_all_categories_removes_filter(self, desktop_page: Page):
        goto_list(desktop_page)
        sidebar_category_select(desktop_page).select_option("0")
        wait_for_list(desktop_page)
        filtered = card_count(desktop_page)

        sidebar_category_select(desktop_page).select_option("")
        wait_for_list(desktop_page)

        assert card_count(desktop_page) >= filtered

    def test_category_combined_with_price(self, desktop_page: Page):
        goto_list(desktop_page)
        sidebar_category_select(desktop_page).select_option("0")
        desktop_page.get_by_placeholder("До").fill("50000")
        wait_for_list(desktop_page)

        cats = get_category_texts(desktop_page)
        if cats:
            assert all("Электроника" in c for c in cats)


class TestUrgentToggle:

    def _toggle(self, page: Page) -> None:
        page.locator("label[class*='urgentToggle']").click()
        wait_for_list(page)

    def test_urgent_toggle_is_visible(self, desktop_page: Page):
        goto_list(desktop_page)
        expect(desktop_page.locator("label[class*='urgentToggle']")).to_be_visible()

    def test_urgent_toggle_reduces_card_count(self, desktop_page: Page):
        goto_list(desktop_page)
        initial = card_count(desktop_page)
        self._toggle(desktop_page)
        assert card_count(desktop_page) <= initial

    def test_urgent_toggle_only_urgent_cards(self, desktop_page: Page):
        goto_list(desktop_page)
        self._toggle(desktop_page)

        total = card_count(desktop_page)
        badges = get_priority_badges(desktop_page)
        assert total > 0
        assert badges == total, f"[BUG-UI-014] Only {badges}/{total} cards have 'Срочно' badge."

    def test_disabling_toggle_restores_list(self, desktop_page: Page):
        goto_list(desktop_page)
        initial = card_count(desktop_page)
        self._toggle(desktop_page)
        self._toggle(desktop_page)
        assert card_count(desktop_page) >= initial


class TestStatsTimer:

    def test_stats_page_loads(self, desktop_page: Page):
        goto_stats(desktop_page)
        expect(desktop_page.locator("body")).not_to_contain_text("Page not found")

    def test_refresh_button_works(self, desktop_page: Page):
        goto_stats(desktop_page)
        btn = desktop_page.locator("button[aria-label='Обновить сейчас']")
        expect(btn).to_be_visible()
        btn.click()
        desktop_page.wait_for_timeout(500)
        expect(desktop_page.locator("body")).to_be_visible()

    def test_countdown_visible_on_load(self, desktop_page: Page):
        goto_stats(desktop_page)
        expect(desktop_page.get_by_text("Обновление через:")).to_be_visible()

    def test_pause_button_stops_timer(self, desktop_page: Page):
        goto_stats(desktop_page)
        desktop_page.locator("button[aria-label='Отключить автообновление']").click()
        desktop_page.wait_for_timeout(400)
        expect(desktop_page.get_by_text("Автообновление выключено")).to_be_visible()

    def test_play_button_restarts_timer(self, desktop_page: Page):
        goto_stats(desktop_page)
        desktop_page.locator("button[aria-label='Отключить автообновление']").click()
        desktop_page.wait_for_timeout(400)
        desktop_page.locator("button[aria-label='Включить автообновление']").click()
        desktop_page.wait_for_timeout(400)
        assert desktop_page.get_by_text("Обновление через:").is_visible(), (
            "[BUG-UI-015] Timer did not restart after clicking 'Включить автообновление'."
        )

    def test_period_select_changes_data(self, desktop_page: Page):
        goto_stats(desktop_page)
        period_select = desktop_page.locator("select#period-select")
        expect(period_select).to_be_visible()

        period_select.select_option("today")
        desktop_page.wait_for_load_state("networkidle")
        desktop_page.wait_for_timeout(500)

        period_select.select_option("30days")
        desktop_page.wait_for_load_state("networkidle")
        desktop_page.wait_for_timeout(500)
        expect(desktop_page.locator("body")).to_be_visible()


class TestThemeToggle:

    def _current_theme(self, page: Page) -> str:
        return page.evaluate(
            "() => document.documentElement.getAttribute('data-theme') || 'light'"
        )

    def _ensure_light(self, page: Page) -> None:
        if self._current_theme(page) == "dark":
            btn = page.locator("button[aria-label='Switch to light theme']")
            btn.wait_for(state="visible", timeout=10000)
            btn.click()
            page.wait_for_timeout(200)

    def _ensure_dark(self, page: Page) -> None:
        if self._current_theme(page) == "light":
            btn = page.locator("button[aria-label='Switch to dark theme']")
            btn.wait_for(state="visible", timeout=10000)
            btn.click()
            page.wait_for_timeout(200)

    def test_toggle_button_visible_on_mobile(self, mobile_page: Page):
        goto_list(mobile_page)
        expect(mobile_page.locator("button[aria-label*='Switch to']")).to_be_visible()

    def test_switch_to_dark(self, mobile_page: Page):
        goto_list(mobile_page)
        self._ensure_light(mobile_page)
        mobile_page.locator("button[aria-label='Switch to dark theme']").click()
        mobile_page.wait_for_timeout(200)
        assert self._current_theme(mobile_page) == "dark"

    def test_switch_back_to_light(self, mobile_page: Page):
        goto_list(mobile_page)
        self._ensure_dark(mobile_page)
        mobile_page.locator("button[aria-label='Switch to light theme']").click()
        mobile_page.wait_for_timeout(200)
        assert self._current_theme(mobile_page) == "light"

    def test_theme_persists_after_reload(self, mobile_page: Page):
        goto_list(mobile_page)
        self._ensure_dark(mobile_page)
        mobile_page.reload()
        mobile_page.wait_for_load_state("networkidle")
        mobile_page.wait_for_timeout(1000)
        assert self._current_theme(mobile_page) == "dark"

    def test_theme_applies_on_stats_page(self, mobile_page: Page):
        goto_list(mobile_page)
        self._ensure_dark(mobile_page)
        mobile_page.locator("a[href='/stats']").click()
        mobile_page.wait_for_load_state("networkidle")
        assert self._current_theme(mobile_page) == "dark"

    def test_button_label_updates_after_toggle(self, mobile_page: Page):
        goto_list(mobile_page)
        self._ensure_light(mobile_page)
        btn = mobile_page.locator("button[aria-label='Switch to dark theme']")
        expect(btn).to_be_visible()
        btn.click()
        mobile_page.wait_for_timeout(200)
        expect(mobile_page.locator("button[aria-label='Switch to light theme']")).to_be_visible()


class TestPriorityDropdown:

    def test_priority_dropdown_urgent_only(self, desktop_page: Page):
        goto_list(desktop_page)
        sidebar_priority_select(desktop_page).select_option("urgent")
        wait_for_list(desktop_page)

        total = card_count(desktop_page)
        badges = get_priority_badges(desktop_page)
        assert total > 0
        assert badges == total, (
            f"[BUG-UI-016] Only {badges}/{total} cards have 'Срочно' badge with priority=urgent."
        )


class TestSearchSlash:

    def test_slash_can_be_typed_in_search_field(self, desktop_page: Page):
        goto_list(desktop_page)
        inp = search_by_title_input(desktop_page)
        expect(inp).to_be_visible()
        inp.click()
        desktop_page.keyboard.type("часть1", delay=15)
        desktop_page.keyboard.type("/", delay=15)
        desktop_page.keyboard.type("часть2", delay=15)
        assert "/" in inp.input_value(), (
            "[BUG-UI-019] Символ «/» не вставляется в строку поиска при наборе с клавиатуры."
        )


class TestStatsMetrics:

    def test_approved_and_rejected_shares_sum_to_100_percent(self, desktop_page: Page):
        goto_stats(desktop_page)
        approved, rejected, _ = parse_stats_metrics(desktop_page.locator("body").inner_text())
        assert approved is not None and rejected is not None, "Не удалось распарсить проценты на /stats"
        assert approved + rejected == 100, (
            f"[BUG-UI-018] Одобрено + отклонено ≠ 100%: {approved}% + {rejected}% = {approved + rejected}%."
        )

    def test_average_moderation_time_is_plausible(self, desktop_page: Page):
        goto_stats(desktop_page)
        _, _, avg_min = parse_stats_metrics(desktop_page.locator("body").inner_text())
        assert avg_min is not None, "Не удалось распарсить среднее время на /stats"
        max_reasonable_minutes = 24 * 60
        assert avg_min <= max_reasonable_minutes, (
            f"[BUG-UI-018] Нереалистичное среднее время: {avg_min} мин (лимит {max_reasonable_minutes} мин)."
        )
