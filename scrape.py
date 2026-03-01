from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, Tag, NavigableString
import json
import re
import time

url = "https://www.wpstud.com/UmaMusume/UmaAbility.htm"

all_skills = {}

def clean_text(t):
    if not t:
        return ''
    t = re.sub(r'[◯◎○□△★◇◆☆◼︎▽▲▼△○◎◇◆★☆□△◇◆◯・/]+', '', t)
    t = re.sub(r'\d+\.?\d*[【[]?[バPt/～~%～～～]+[】\]]?', '', t)
    t = re.sub(r'\(.*?\)|【.*?】|\[.*?\]|\{.*?\}', '', t)
    t = re.sub(r'\s+', '', t).strip()
    return t

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
    page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    print(f"正在載入 {url} ...")
    page.goto(url, wait_until="networkidle", timeout=120000)
    page.wait_for_timeout(10000)
    
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    browser.close()

all_tables = soup.find_all('table')
print(f"全頁找到 {len(all_tables)} 個 table")

if len(all_tables) < 2:
    print("Table 數量不足！")
    exit()

# ====================
# 第一部分：一般技能 - 尾二個 table
# ====================
print("--- 處理一般技能 (尾二 table) ---")
normal_table = all_tables[-2]
rows = normal_table.find_all('tr')[1:]  # skip title
for row in rows:
    cells = row.find_all('td')
    if len(cells) >= 2:
        cn_raw = cells[1].get_text(strip=True)
        if cn_raw:
            jp_name = clean_text(cells[0].get_text(strip=True))
            cn_name = clean_text(cn_raw)
            if jp_name and cn_name:
                all_skills[jp_name] = cn_name
                print(f"一般: {jp_name} → {cn_name}")
# ====================
# 第二部分：固有技能 - 最尾個 table
# ====================
print("--- 處理固有技能 (最尾 table) ---")
unique_table = all_tables[-1]
rows = unique_table.find_all('tr')[1:]  # 跳過第一個 tr
for row in rows:
    cells = row.find_all('td')
    if len(cells) < 2:
        continue
    
    target_td = cells[1]  # 只睇第二格
    text_raw = target_td.get_text(separator="\n", strip=True)
    if not text_raw:
        continue
    
    # debug 原始內容
    print("原始固有 td:", text_raw[:80])
    
    # 強力 filter：含有 1. 或 2. 就 skip（你新要求）
    if re.search(r'1\.|2\.', text_raw):
        print("含有 1. 或 2.，跳過（條件說明）:", text_raw[:50])
        continue
    
    # 其他條件說明關鍵詞
    skip_keywords = r'育成事件|勝出最少|擁有最少|または|或|ファン数|スタミナ|パワー|スピード|根性|賢さ|距離|重賞|G1|G2|U.A.F|回[+-]|速[+-]|加速力[+-]|額外条件|効果変更|条件変更'
    if re.search(skip_keywords, text_raw):
        print("其他條件說明，跳過:", text_raw[:50])
        continue
    
    # 冇假名 → 跳過
    if not re.search(r'[\u3040-\u30ff]', text_raw):
        print("冇假名，跳過:", text_raw[:50])
        continue
    
    jp_res = ""
    cn_res = ""
    
    # 優先 / 分隔
    if '/' in text_raw:
        parts = text_raw.split('/', 1)
        jp_res = parts[0].strip()
        cn_res = parts[1].strip()
    else:
        # 用 \n 分隔
        lines = [line.strip() for line in text_raw.split('\n') if line.strip()]
        if len(lines) >= 2:
            jp_res = lines[0]
            cn_res = lines[1]
        elif len(lines) == 1:
            jp_res = lines[0]
            cn_res = ""
        else:
            jp_res = text_raw.strip()
            cn_res = ""
    
    jp_f = clean_text(jp_res)
    cn_f = clean_text(cn_res)
    
    # 最終確認：日文要有假名或漢字，且長度合理
    if jp_f and re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]', jp_f) and len(jp_f) > 3:
        all_skills[jp_f] = cn_f or jp_f
        print(f"固有: {jp_f} → {cn_f or '(無中文)'} (原jp: {jp_res[:50]})")
    else:
        print("日文無效，跳過:", jp_res[:50])
