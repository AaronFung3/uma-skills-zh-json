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
print("--- 處理：全表掃描 (排除 rowspan 並執行極狠 Filter) ---")
# 攞最後兩個 table (一般技能同固有技能)
target_tables = all_tables[-2:]

for table in target_tables:
    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        for td in cells:
            # 1. 排除有 rowspan 嘅 td (通常係分類標籤)
            if td.has_attr('rowspan'):
                continue
            
            # 2. 攞純文字做極狠 Filter
            full_text = td.get_text(strip=True)
            
            # 如果見到 1. 2. + → 或者效果字眼，直接成個 td 唔要
            if not full_text or re.search(r'1\.|2\.|3\.|\+|＋|→|->|效果|條件|加速|速度|回復|以上|以下|、', full_text):
                continue
            
            # 3. 檢查有無日文假名 (確保係技能名，唔係純數字或純符號)
            if not re.search(r'[\u3040-\u309f\u30a0-\u30ff]', full_text):
                continue

            jp_res, cn_res = "", ""
            classes = td.get('class', [])

            # 4. 依照 class="forth" 或 <br> 邏輯提取
            if 'forth' in classes:
                if '/' in full_text:
                    parts = full_text.split('/', 1)
                    jp_res, cn_res = parts[0], parts[1]
            else:
                br = td.find('br')
                if br:
                    prev = [s for s in br.previous_siblings if isinstance(s, (str, NavigableString))]
                    jp_res = "".join(reversed([str(s) for s in prev])).strip()
                    nxt = [s for s in br.next_siblings if isinstance(s, (str, NavigableString))]
                    cn_res = "".join([str(s) for s in nxt]).strip()

            # 5. 清理並存檔
            jp_f = clean_text(jp_res)
            cn_f = clean_text(cn_res)

            if jp_f and cn_f:
                all_skills[jp_f] = cn_f
                print(f"✅ 成功提取: {jp_f} -> {cn_f}")

# 寫入 JSON
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"\n全部完成！一共執到 {len(all_skills)} 組純淨技能名。")
