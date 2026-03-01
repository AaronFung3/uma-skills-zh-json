from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, Tag, NavigableString  # 關鍵：加返 Tag 同 NavigableString
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
for row in unique_table.find_all('tr'):
    cells = row.find_all('td')
    if len(cells) < 2:
        continue
    
    target_td = cells[1]  # 只睇第二格
    classes = target_td.get('class', [])
    
    jp_res = ""
    cn_res = ""
    
    if 'forth' in classes:
        txt = target_td.get_text(strip=True)
        if '/' in txt:
            parts = txt.split('/', 1)
            jp_res = parts[0].strip()
            cn_res = parts[1].strip()
    else:
        br = target_td.find('br')
        if br:
            # br 前所有文字為日文
            prev_sibs = []
            sib = br.previous_sibling
            while sib:
                if isinstance(sib, NavigableString):
                    prev_sibs.append(sib.strip())
                sib = sib.previous_sibling
            jp_res = ''.join(reversed(prev_sibs))
            
            # br 後所有文字為中文（只取到下一個 br 或結束）
            nxt_sibs = []
            sib = br.next_sibling
            while sib:
                if isinstance(sib, NavigableString):
                    nxt_sibs.append(sib.strip())
                if isinstance(sib, Tag) and sib.name == 'br':
                    break
                sib = sib.next_sibling
            cn_res = ''.join(nxt_sibs)
    
    jp_f = clean_text(jp_res)
    cn_f = clean_text(cn_res)
    if jp_f and cn_f:
        all_skills[jp_f] = cn_f
        print(f"固有: {jp_f} → {cn_f} (原jp: {jp_res[:50]})")

# 儲存
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"\n完成！總共抓取 {len(all_skills)} 個技能。")
