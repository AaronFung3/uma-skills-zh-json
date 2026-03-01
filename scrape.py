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
    t = re.sub(r'[◯◎○□△★◇◆☆◼︎▽▲▼△○◎◇◆★☆□△◇◆◯]+', '', t)  # 移除所有符號
    t = re.sub(r'\d+\.?\d*[【[]?[バPt/～~%～～]+[】\]]?', '', t)  # 移除數字 [バ] 等
    t = re.sub(r'\(.*?\)|【.*?】|\[.*?\]|\{.*?\}', '', t)  # 移除括號
    t = re.sub(r'\s+|/|・', '', t).strip()  # 移除空格 / ・
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
            page.wait_for_timeout(12000)  # 多等
            html = page.content()
            break
        except Exception as e:
            print(f"失敗: {e}")
            time.sleep(5)

    if not html:
        print("載入失敗")
        browser.close()
        exit(1)

    soup = BeautifulSoup(html, 'html.parser')
    browser.close()

# ====================
# 第一部分：限定條件表
# ====================
print("處理限定條件表...")

found_condition = False
condition_keywords = ["出現兩個或以上限定條件時", "兩個條件都要附合", "先行・長距離", "中距離/長距離"]

for string in soup.find_all(string=True):
    str_text = string.strip()
    if any(kw in str_text for kw in condition_keywords):
        found_condition = True
        print(f"找到限定關鍵句: {str_text[:50]}...")
        
        # 從該 string 開始，向下找第一個 table
        current = string.parent
        table = None
        while current and not table:
            table = current.find_next('table')
            if table:
                break
            current = current.parent if hasattr(current, 'parent') else None
        
        if table:
            rows = table.find_all('tr')
            if len(rows) > 1:
                for row in rows[1:]:  # skip title
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
            # 只處理呢個 table，stop 避免捉埋下面
            break

if not found_condition:
    print("冇搵到限定關鍵句，fallback 全頁 table...")
    # fallback 掃所有 table 的第二格
    for table in soup.find_all('table'):
        rows = table.find_all('tr')[1:]
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2 and cells[1].get_text(strip=True):
                jp = clean_text(cells[0].get_text(strip=True))
                cn = clean_text(cells[1].get_text(strip=True))
                if jp and cn:
                    all_skills[jp] = cn
                    print(f"fallback 限定: {jp} → {cn}")

# ====================
# 第二部分：固有技能
# ====================
print("處理固有技能...")

unique_keywords = ["符合繼承固有的進化條件時直接進化無需選擇", "設定, 符合繼承固有的進化條件時"]

found_unique = False
for string in soup.find_all(string=True):
    str_text = string.strip()
    if any(kw in str_text for kw in unique_keywords):
        found_unique = True
        print(f"找到固有關鍵句: {str_text[:50]}...")
        
        current = string.parent.next_element
        while current:
            if isinstance(current, Tag) and current.name == 'td':
                # 只處理第二格 td (假設每行第一格空或標題，第二格內容)
                prev_td = current.find_previous_sibling('td')
                if prev_td and prev_td.get_text(strip=True) == '':  # 第一格空 → 第二格
                    td = current
                    jp = ""
                    cn = ""
                    
                    if 'forth' in td.get('class', []):
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
                    else:
                        br = td.find('br')
                        if br:
                            jp = ''.join(str(s).strip() for s in br.previous_siblings if isinstance(s, NavigableString))
                            cn = ''.join(str(s).strip() for s in br.next_siblings if isinstance(s, NavigableString))
                    
                    jp_clean = clean_text(jp)
                    cn_clean = clean_text(cn)
                    if jp_clean and cn_clean:
                        all_skills[jp_clean] = cn_clean
                        print(f"固有插入: {jp_clean} → {cn_clean}")
            current = current.next_element if hasattr(current, 'next_element') else None
        break

if not found_unique:
    print("冇搵到固有關鍵句！")

# 寫入
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"總共抓取 {len(all_skills)} 個技能，已寫入 skills.json")
