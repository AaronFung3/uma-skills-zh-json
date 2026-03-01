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
    # 移除所有符號、數字、括號、[バ] 等，只保留核心文字
    t = re.sub(r'[◯◎○□△★◇◆☆◼︎▽▲▼△○◎◇◆★☆□△◇◆◯]+', '', t)
    t = re.sub(r'\d+\.?\d*[【[]?[バPt/～~%～～～]+[】\]]?', '', t)
    t = re.sub(r'\(.*?\)|【.*?】|\[.*?\]|\{.*?\}', '', t)
    t = re.sub(r'\s+', '', t).strip()
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
# 第一部分：限定條件表
# ====================
print("處理限定條件表...")

condition_key = "出現兩個或以上限定條件時中間顯示\"・\"為兩個條件都要附合"

found = False
for p in soup.find_all('p'):
    text = p.get_text(strip=True)
    if condition_key in text:
        found = True
        print("找到限定條件說明句！")
        
        # 從這個 p 開始，向下找第一個 table
        table = p.find_next('table')
        if table:
            print("找到限定條件表！第一行文字：", table.find('tr').get_text(strip=True)[:50] if table.find('tr') else "無")
            rows = table.find_all('tr')[1:]  # skip 第一行 title
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
                    print(f"限定: {jp_clean} → {cn_clean}")
        else:
            print("說明句下面冇 table！")
        break

if not found:
    print("冇搵到限定條件說明句！")

# ====================
# 第二部分：固有技能
# ====================
print("處理固有技能...")

unique_key = "設定, 符合繼承固有的進化條件時直接進化無需選擇"

found = False
for p in soup.find_all('p'):
    text = p.get_text(strip=True)
    if unique_key in text:
        found = True
        print("找到固有說明句！")
        
        # 從這個 p 開始，向下找所有 td，只處理第二格
        current = p.next_element
        while current:
            if isinstance(current, Tag) and current.name == 'td':
                # 判斷是否第二格（假設每行第一格空或標題）
                prev_sib = current.find_previous_sibling('td')
                if not prev_sib or not prev_sib.get_text(strip=True):
                    td = current
                    jp = ""
                    cn = ""
                    
                    if 'forth' in td.get('class', []):
                        # 有 class="forth" → 優先 / 分隔
                        text_full = td.get_text(separator="/", strip=True)
                        if '/' in text_full:
                            parts = text_full.split('/', 1)
                            jp = parts[0].strip()
                            cn = parts[1].strip()
                    else:
                        # 冇 class → 用 <br>
                        br = td.find('br')
                        if br:
                            # <br> 前所有文字為日文
                            jp_parts = [s.strip() for s in br.previous_siblings if isinstance(s, NavigableString)]
                            jp = ''.join(reversed(jp_parts))
                            # <br> 後所有文字為中文
                            cn_parts = [s.strip() for s in br.next_siblings if isinstance(s, NavigableString)]
                            cn = ''.join(cn_parts)
                    
                    jp_clean = clean_text(jp)
                    cn_clean = clean_text(cn)
                    if jp_clean and cn_clean:
                        all_skills[jp_clean] = cn_clean
                        print(f"固有: {jp_clean} → {cn_clean} (原jp: {jp[:50]})")
            current = current.next_element if hasattr(current, 'next_element') else None
        break

if not found:
    print("冇搵到固有說明句！")

# 寫入 JSON
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"總共抓取 {len(all_skills)} 個技能，已寫入 skills.json")
