from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, NavigableString, Tag
import json
import re
import time

url = "https://www.wpstud.com/UmaMusume/UmaAbility.htm"

all_skills = {}  # 日文清理後 → 中文

def clean_text(t):
    if not t:
        return ''
    t = re.sub(r'[◯◎○□△★◇◆☆◼︎▽▲▼△○◎◇◆★☆□△◇◆◯]+', '', t)
    t = re.sub(r'\d+\.?\d*[【[]?[バPt/～~%～～]+[】\]]?', '', t)
    t = re.sub(r'\(.*?\)|【.*?】|\[.*?\]|\{.*?\}', '', t)
    t = re.sub(r'\s+|/|・', '', t).strip()
    return t

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
    page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
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

# ====================
# 第一部分：限定條件表 - 先 save 目標 table
# ====================
print("處理限定條件表...")

found_condition_table = None
condition_keywords = ["出現兩個或以上限定條件時", "兩個條件都要附合", "先行・長距離", "中距離/長距離"]

for string in soup.find_all(string=True):
    str_text = string.strip()
    if any(kw in str_text for kw in condition_keywords):
        print(f"找到限定關鍵句: {str_text[:80]}...")
        
        # 從呢個 string 開始，向下找第一個 table，並 save 低
        current = string.parent
        while current and not found_condition_table:
            next_tables = current.find_all_next('table', limit=3)  # 只試最近 3 個，避免太遠
            for t in next_tables:
                # 檢查 table 有冇 rows 且第二格有內容
                rows = t.find_all('tr')
                if len(rows) > 1 and any(cell.get_text(strip=True) for row in rows[1:] for cell in row.find_all('td')[1:]):
                    found_condition_table = t
                    print("成功 save 限定表 table！第一行文字：", rows[0].get_text(strip=True)[:50])
                    break
            current = current.next_sibling if hasattr(current, 'next_sibling') else None
        
        if found_condition_table:
            # 只處理呢個 table
            rows = found_condition_table.find_all('tr')[1:]  # skip title
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
            break  # 搵到就 stop，不再繼續向下

if not found_condition_table:
    print("冇搵到限定條件表！")

# ====================
# 第二部分：固有技能 - 同樣先 save 目標 table
# ====================
print("處理固有技能...")

found_unique_table = None
unique_keywords = ["符合繼承固有的進化條件時直接進化無需選擇", "設定, 符合繼承固有的進化條件時"]

for string in soup.find_all(string=True):
    str_text = string.strip()
    if any(kw in str_text for kw in unique_keywords):
        print(f"找到固有關鍵句: {str_text[:80]}...")
        
        current = string.parent
        while current and not found_unique_table:
            next_tables = current.find_all_next('table', limit=5)
            for t in next_tables:
                rows = t.find_all('tr')
                if rows:
                    found_unique_table = t
                    print("成功 save 固有 table！第一行文字：", rows[0].get_text(strip=True)[:50] if rows[0] else "無")
                    break
            current = current.next_sibling if hasattr(current, 'next_sibling') else None
        
        if found_unique_table:
            rows = found_unique_table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 2:
                    continue
                td = cells[1]
                jp = ""
                cn = ""
                
                # 優先 / 分隔
                text = td.get_text(separator="/", strip=True)
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
                    print(f"固有插入: {jp_clean} → {cn_clean} (原jp: {jp[:50]})")
            break

if not found_unique_table:
    print("冇搵到固有技能表！")

# 寫入 JSON
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"總共抓取 {len(all_skills)} 個技能，已寫入 skills.json")
