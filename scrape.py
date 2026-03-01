from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, NavigableString, Tag
import json
import re
import time

url = "https://www.wpstud.com/UmaMusume/UmaAbility.htm"

all_skills = {}  # 最終合併 dict：日文清理後 → 中文

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
    page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"嘗試 {attempt + 1} 載入...")
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            page.wait_for_timeout(8000)  # 多等確保內容載入
            html = page.content()
            break
        except Exception as e:
            print(f"失敗: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(5)

    soup = BeautifulSoup(html, 'html.parser')
    browser.close()

# ====================
# 第一部分：限定條件表
# ====================
print("開始處理限定條件表...")

tables = soup.find_all('table')
target_table = None

for table in tables:
    text_around = table.find_previous(string=True, recursive=False)
    if text_around and "出現兩個或以上限定條件時中間顯示" in text_around:
        target_table = table
        break

if target_table:
    rows = target_table.find_all('tr')[1:]  # skip 第一行
    for row in rows:
        cells = row.find_all(['td', 'th'])
        if len(cells) < 2:
            continue
        cn_cell = cells[1].get_text(strip=True)
        if not cn_cell:  # 第二格冇嘢 → skip
            continue
        
        jp = cells[0].get_text(strip=True)
        cn = cn_cell
        
        # 兩邊清理符號，只保留文字
        jp_clean = re.sub(r'[◯◎○□△★◇◆☆]+', '', jp).strip()
        cn_clean = re.sub(r'[◯◎○□△★◇◆☆]+', '', cn).strip()
        
        if jp_clean:
            all_skills[jp_clean] = cn_clean
            print(f"限定表: {jp_clean} → {cn_clean} (原jp: {jp})")
else:
    print("冇搵到限定條件表！")

# ====================
# 第二部分：固有技能
# ====================
print("開始處理固有技能...")

target_text = "設定, 符合繼承固有的進化條件時直接進化無需選擇"
target_p = None
for p in soup.find_all('p'):
    if target_text in p.get_text(strip=True):
        target_p = p
        break

if target_p:
    # 從呢個 p 之後的所有 td 第二格
    current = target_p.next_sibling
    while current:
        if isinstance(current, Tag) and current.name == 'table':
            # 固有技能通常係 table 內第二格
            for row in current.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                td = cells[1]  # 第二格
                
                jp = ""
                cn = ""
                
                if 'forth' in td.get('class', []):
                    # class="forth" → 優先 / 分隔
                    text = td.get_text(separator="/", strip=True)
                    if '/' in text:
                        parts = text.split('/', 1)
                        jp = parts[0].strip()
                        cn = parts[1].strip()
                    else:
                        # 冇 / 就用 <br>
                        br = td.find('br')
                        if br:
                            jp = ''.join(str(c).strip() for c in br.previous_siblings if isinstance(c, NavigableString)).strip()
                            cn = ''.join(str(c).strip() for c in br.next_siblings if isinstance(c, NavigableString)).strip()
                else:
                    # 冇 class → 用 <br>
                    br = td.find('br')
                    if br:
                        jp = ''.join(str(c).strip() for c in br.previous_siblings if isinstance(c, NavigableString)).strip()
                        cn = ''.join(str(c).strip() for c in br.next_siblings if isinstance(c, NavigableString)).strip()
                
                if jp and cn:
                    # 清理符號
                    jp_clean = re.sub(r'[◯◎○□△★◇◆☆]+', '', jp).strip()
                    cn_clean = re.sub(r'[◯◎○□△★◇◆☆]+', '', cn).strip()
                    if jp_clean:
                        all_skills[jp_clean] = cn_clean
                        print(f"固有: {jp_clean} → {cn_clean} (原jp: {jp})")
        current = current.next_sibling
else:
    print("冇搵到固有技能標題！")

# 寫入 JSON
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"總共抓取 {len(all_skills)} 個技能，已寫入 skills.json")
