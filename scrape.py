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
    # 移除符號、數字、括號內容、[バ] 等
    t = re.sub(r'[◯◎○□△★◇◆☆◼︎▽▲▼△○◎◇◆★☆□△◇◆]+', '', t)
    t = re.sub(r'\d+\.?\d*[【[]?[バPt/～~%]+[】\]]?', '', t)
    t = re.sub(r'\(.*?\)|【.*?】|\[.*?\]', '', t)
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
            page.wait_for_timeout(10000)  # 多等確保全載入
            html = page.content()
            break
        except Exception as e:
            print(f"失敗: {e}")
            time.sleep(5)

    if not html:
        print("載入失敗，退出")
        browser.close()
        exit(1)

    soup = BeautifulSoup(html, 'html.parser')
    browser.close()

# ====================
# 第一部分：限定條件表
# ====================
print("開始處理限定條件表...")

found_condition = False
for string in soup.find_all(string=re.compile(r"出現兩個或以上限定條件時中間顯示.*出現兩個或以上限定條件時", re.I)):
    found_condition = True
    parent = string.find_parent(['p', 'div', 'td'])
    if parent:
        table = parent.find_next('table')
        if table:
            rows = table.find_all('tr')[1:]  # skip title
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
        break

if not found_condition:
    print("冇搵到限定條件關鍵句！試全頁 table fallback...")
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
print("開始處理固有技能...")

found_unique = False
for string in soup.find_all(string=re.compile(r"符合繼承固有的進化條件時直接進化無需選擇", re.I)):
    found_unique = True
    parent = string.find_parent(['p', 'div'])
    if parent:
        current = parent.next_element
        while current:
            if isinstance(current, Tag) and current.name == 'td':
                if len(current.find_all_previous('td')) % 2 == 1:  # 第二格 (index odd)
                    td = current
                    jp = ""
                    cn = ""
                    
                    if 'forth' in td.get('class', []):
                        text = td.get_text(separator="|", strip=True)
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
                        print(f"固有: {jp_clean} → {cn_clean}")
            current = current.next_element if hasattr(current, 'next_element') else None
    break

if not found_unique:
    print("冇搵到固有關鍵句！")

# 輸出
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"總共抓取 {len(all_skills)} 個技能，已寫入 skills.json")
