from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import re
import time

url = "https://www.wpstud.com/UmaMusume/UmaAbility.htm"

all_skills = {}

def clean_text(t):
    if not t:
        return ''
    t = re.sub(r'[◯◎○□△★◇◆☆◼︎▽▲▼△○◎◇◆★☆□△◇◆◯]+', '', t)
    t = re.sub(r'\d+\.?\d*[【[]?[バPt/～~%～～～]+[】\]]?', '', t)
    t = re.sub(r'\(.*?\)|【.*?】|\[.*?\]|\{.*?\}', '', t)
    t = re.sub(r'\s+|/|・', '', t).strip()
    return t

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
    page = browser.new_page()
    
    max_retries = 3
    html = None
    for attempt in range(max_retries):
        try:
            print(f"嘗試 {attempt + 1} 載入...")
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(15000)
            html = page.content()
            break
        except Exception as e:
            print(f"失敗: {e}")
            time.sleep(5)

    soup = BeautifulSoup(html, 'html.parser')
    browser.close()

# 限定條件表 - 先搵關鍵句，然後嚴格確認 table
print("處理限定條件表...")
found_condition_table = None
condition_keywords = ["出現兩個或以上限定條件時", "兩個條件都要附合", "先行・長距離", "中距離/長距離"]

for string in soup.find_all(string=True):
    str_text = string.strip()
    if any(kw in str_text for kw in condition_keywords):
        print(f"找到限定關鍵句: {str_text[:80]}...")
        
        # 從該位置開始，只找最近一個合適 table
        current = string.parent
        while current and not found_condition_table:
            table = current.find_next('table')
            if table:
                rows = table.find_all('tr')
                if len(rows) > 2:  # 至少有 header + 1行數據
                    first_row_text = rows[0].get_text(strip=True)
                    if "條件" in first_row_text or "・" in first_row_text or "/" in first_row_text:
                        found_condition_table = table
                        print("確認 save 限定 table！第一行：", first_row_text[:50])
                        break
            current = current.next_sibling

if found_condition_table:
    rows = found_condition_table.find_all('tr')[1:]
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) < 2:
            continue
        cn_text = cells[1].get_text(strip=True)
        if not cn_text:
            continue
        jp_text = cells[0].get_text(strip=True)
        jp_clean = clean_text(jp_text)
        cn_clean = clean_text(cn_text)
        if jp_clean and cn_clean:
            all_skills[jp_clean] = cn_clean
            print(f"限定插入: {jp_clean} → {cn_clean}")
else:
    print("未能確認限定 table！")

# 固有技能 - 同樣 save 表
print("處理固有技能...")
found_unique_table = None
unique_keywords = ["符合繼承固有的進化條件時直接進化無需選擇", "設定, 符合繼承固有的進化條件時"]

for string in soup.find_all(string=True):
    str_text = string.strip()
    if any(kw in str_text for kw in unique_keywords):
        print(f"找到固有關鍵句: {str_text[:80]}...")
        
        current = string.parent
        while current and not found_unique_table:
            table = current.find_next('table')
            if table:
                rows = table.find_all('tr')
                if len(rows) > 1 and any(len(row.find_all('td')) >= 2 for row in rows):
                    found_unique_table = table
                    print("確認 save 固有 table！第一行：", rows[0].get_text(strip=True)[:50] if rows[0] else "無")
                    break
            current = current.next_sibling

if found_unique_table:
    rows = found_unique_table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 2:
            continue
        td = cells[1]
        text = td.get_text(strip=True)
        if not text:
            continue
        
        jp = ""
        cn = ""
        
        # 優先 / 分隔
        if '/' in text:
            parts = text.split('/', 1)
            jp = parts[0].strip()
            cn = parts[1].strip()
        else:
            br = td.find('br')
            if br:
                jp = ''.join(str(s).strip() for s in br.previous_siblings if isinstance(s, NavigableString))
                cn = ''.join(str(s).strip() for s in br.next_siblings if isinstance(s, NavigableString))
        
        jp_clean = clean_text(jp)
        cn_clean = clean_text(cn)
        if jp_clean and cn_clean:
            all_skills[jp_clean] = cn_clean
            print(f"固有插入: {jp_clean} → {cn_clean} (原jp: {jp})")
else:
    print("未能確認固有 table！")

# 輸出
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"總共抓取 {len(all_skills)} 個技能，已寫入 skills.json")
