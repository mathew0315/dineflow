"""瀏覽器端對端測試。

流程：顧客點餐 → 老闆看板推進 → 顧客頁自動變「可取餐」→ POS → 改價/售完 → 報表 → QR → 店員權限 → 錯誤處理

執行前先以 DEMO_MODE=true 啟動服務（示範店資料需為初始狀態）：
    DEMO_MODE=true uvicorn app.main:app --port 8000 &
    python e2e/demo_flow.py
"""
import os
import sys

from playwright.sync_api import expect, sync_playwright

B = os.getenv("BASE_URL", "http://localhost:8000")
OUT = os.getenv("SHOTS_DIR", "e2e-shots")
os.makedirs(OUT, exist_ok=True)
errors: list[str] = []


def watch(page, tag):
    page.on("console", lambda m: m.type == "error" and errors.append(f"[{tag}] console: {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"[{tag}] pageerror: {e}"))


with sync_playwright() as p:
    br = p.chromium.launch()

    # ---------- 首頁（桌機） ----------
    desk = br.new_page(viewport={"width": 1280, "height": 860})
    watch(desk, "home")
    desk.goto(B + "/")
    expect(desk.get_by_role("heading", name="小吃店的點菜單，搬到手機上。")).to_be_visible()
    desk.screenshot(path=f"{OUT}/01_home.png", full_page=True)

    # ---------- 顧客點餐（手機） ----------
    phone = br.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2)
    watch(phone, "customer")
    phone.goto(B + "/s/demo")
    expect(phone.get_by_text("阿明麵食館（示範店）")).to_be_visible()
    phone.get_by_role("button", name="擔仔麵 加一份").click()
    phone.get_by_role("button", name="擔仔麵 加一份").click()
    phone.get_by_role("button", name="滷蛋 加一份").click()
    expect(phone.get_by_text("NT$125")).to_be_visible()  # 55*2 + 15
    phone.get_by_label("取餐稱呼").fill("測試員")
    phone.get_by_label("手機（查詢取餐進度用）").fill("0987654321")
    phone.get_by_label("備註").fill("麵不要蔥")
    phone.screenshot(path=f"{OUT}/02_order_sheet_mobile.png", full_page=True)
    phone.get_by_role("button", name="送出點單").click()
    expect(phone.get_by_role("status")).to_have_text("已收單")
    order_no = phone.locator(".sheet-head .hand").inner_text().lstrip("#")
    phone.screenshot(path=f"{OUT}/03_track_pending.png", full_page=True)
    print("customer order", order_no)

    # ---------- 老闆登入、看板 ----------
    watch(desk, "admin")
    desk.goto(B + "/login?email=owner%40demo.dineflow.app")
    desk.get_by_role("button", name="登入").click()
    expect(desk.get_by_role("link", name="訂單看板")).to_be_visible()
    ticket = desk.locator(".ticket", has_text=f"#{order_no}")
    expect(ticket).to_be_visible()
    expect(ticket).to_contain_text("麵不要蔥")
    desk.screenshot(path=f"{OUT}/04_board.png", full_page=True)
    ticket.get_by_role("button", name="開始製作").click()
    ticket = desk.locator(".rail-preparing .ticket", has_text=f"#{order_no}")
    ticket.get_by_role("button", name="出餐").click()
    expect(desk.locator(".rail-ready .ticket", has_text=f"#{order_no}")).to_be_visible()

    # 顧客頁 5 秒內自動更新成「可取餐」
    expect(phone.get_by_role("status")).to_have_text("可取餐", timeout=8000)
    phone.screenshot(path=f"{OUT}/05_track_ready.png", full_page=True)

    # ---------- POS ----------
    desk.get_by_role("link", name="POS 點餐").click()
    desk.locator(".pos-item", has_text="滷肉飯").click()
    desk.locator(".pos-item", has_text="滷肉飯").click()
    desk.locator(".pos-item", has_text="貢丸湯").click()
    desk.get_by_label("桌號").fill("B2")
    expect(desk.locator(".pos-ticket .total")).to_contain_text("NT$100")  # 35*2+30
    desk.screenshot(path=f"{OUT}/06_pos.png", full_page=True)
    desk.get_by_role("button", name="收款並送單").click()
    expect(desk.locator(".toast")).to_contain_text("已送進廚房")

    # ---------- 菜單改價 + 售完 ----------
    desk.get_by_role("link", name="菜單").click()
    price = desk.get_by_label("擔仔麵 價格")
    price.fill("60")
    price.press("Enter")
    expect(desk.locator(".toast")).to_contain_text("改為 NT$60")
    desk.locator("tr", has_text="冬瓜茶").get_by_role("button", name="供應中").click()
    expect(desk.locator("tr", has_text="冬瓜茶").get_by_role("button", name="售完")).to_be_visible()
    desk.screenshot(path=f"{OUT}/07_menu.png", full_page=True)

    # 顧客端看不到售完品項、看到新價格
    phone.goto(B + "/s/demo")
    expect(phone.get_by_text("擔仔麵")).to_be_visible()
    expect(phone.get_by_text("冬瓜茶")).to_have_count(0)
    expect(phone.locator("tr", has_text="擔仔麵").locator(".col-price")).to_have_text("60")

    # ---------- 報表 ----------
    desk.get_by_role("link", name="今日報表").click()
    expect(desk.get_by_text("熱銷品項")).to_be_visible()
    desk.screenshot(path=f"{OUT}/08_report.png", full_page=True)
    print("report kpis:", desk.locator(".kpi .v").all_inner_texts())

    # ---------- 設定 / QR ----------
    desk.get_by_role("link", name="店家設定").click()
    expect(desk.locator("svg").first).to_be_visible()
    desk.screenshot(path=f"{OUT}/09_settings_qr.png", full_page=True)
    desk.get_by_role("button", name="暫停接單").click()
    expect(desk.get_by_role("button", name="開始營業")).to_be_visible()
    phone.goto(B + "/s/demo")
    expect(phone.get_by_text("店家目前休息中，暫停接單。")).to_be_visible()
    expect(phone.get_by_role("button", name="送出點單")).to_be_disabled()
    desk.get_by_role("button", name="開始營業").click()

    # ---------- 店員權限 ----------
    staff = br.new_page(viewport={"width": 1024, "height": 768})
    watch(staff, "staff")
    staff.goto(B + "/login?email=staff%40demo.dineflow.app")
    staff.get_by_role("button", name="登入").click()
    expect(staff.get_by_role("link", name="訂單看板")).to_be_visible()
    expect(staff.get_by_role("link", name="今日報表")).to_have_count(0)
    staff.get_by_role("link", name="菜單").click()
    expect(staff.get_by_text("店員可以切換售完")).to_be_visible()
    expect(staff.get_by_label("擔仔麵 價格")).to_have_count(0)

    # ---------- 錯誤處理 ----------
    phone.goto(B + "/s/no-such-store")
    expect(phone.get_by_text("找不到這間店，請確認網址")).to_be_visible()
    staff.goto(B + "/login")
    staff.get_by_label("Email").fill("owner@demo.dineflow.app")
    staff.get_by_label("密碼").fill("wrong-password")
    staff.get_by_role("button", name="登入").click()
    expect(staff.get_by_role("alert")).to_have_text("帳號或密碼錯誤")

    br.close()

# 排除預期內的訊息：刻意測試的 404 / 401，以及無對外網路時的字型載入失敗
EXPECTED = ("404 (Not Found)", "401 (Unauthorized)", "fonts.g", "ERR_")
real = [e for e in errors if not any(x in e for x in EXPECTED)]
print("console/page errors:", real or "none")
sys.exit(1 if real else 0)
