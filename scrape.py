from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, Tag, NavigableString
import json
import re

url = "https://www.wpstud.com/UmaMusume/UmaAbility.htm"

def clean_text(t):
    if not t: return ''
    # 移除符號、括號及其內容、數字單位
    t = re.sub(r'[◯◎○□△★◇◆☆◼︎▽▲▼△○◎◇◆★☆□△◇◆◯・/]+', '', t)
    t = re.sub(r'\(.*?\)|【.*?】|\[.*?\]|\{.*?\}', '', t)
    t = re.sub(r'\d+\.?\d*[バPt/～~%]+', '', t)
    return re.sub(r'\s+', '', t).strip()

all_skills = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print(f"正在載入 {url} ...")
    page.goto(url, wait_until="networkidle")
    
    # 搵出包含內容嘅 Frame
    target_soup = None
    for frame in page.frames:
        f_html = frame.content()
        # 只要 Frame 入面有 table 就係目標
        if "<table" in f_html.lower():
            target_soup = BeautifulSoup(f_html, 'html.parser')
            break
            
    if not target_soup:
        print("搵唔到 Table！")
        browser.close()
        exit()

    all_tables = target_soup.find_all('table')
    if len(all_tables) < 2:
        print("Table 數量不足！")
        browser.close()
        exit()

    # ====================
    # 第一部分：一般技能 (尾二個 Table)
    # ====================
    print("--- 處理：一般技能 (尾二 Table) ---")
    normal_table = all_tables[-2]
    for row in normal_table.find_all('tr')[1:]: # Skip Title
        cells = row.find_all('td')
        if len(cells) >= 2:
            cn_raw = cells[1].get_text(strip=True)
            if cn_raw: # 有中文先捉
                jp_name = clean_text(cells[0].get_text())
                cn_name = clean_text(cn_raw)
                if jp_name and cn_name:
                    all_skills[jp_name] = cn_name

    # ====================
    # 第二部分：固有技能 (最尾個 Table)
    # ====================
    print("--- 處理：固有技能 (最尾 Table) ---")
    unique_table = all_tables[-1]
    for row in unique_table.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 2: continue
        
        target_td = cells[1] # 只睇第二格
        classes = target_td.get('class', [])
        
        jp_res, cn_res = "", ""
        
        if 'forth' in classes:
            # 邏輯：有 / 就分開
            txt = target_td.get_text(strip=True)
            if '/' in txt:
                parts = txt.split('/', 1)
                jp_res, cn_res = parts[0], parts[1]
        else:
            # 邏輯：用 <br> 分開
            br = target_td.find('br')
            if br:
                # 攞 br 前面所有文字
                prev = [s for s in br.previous_siblings if isinstance(s, (str, NavigableString))]
                jp_res = "".join(reversed([str(s) for s in prev])).strip()
                # 攞 br 後面所有文字
                nxt = [s for s in br.next_siblings if isinstance(s, (str, NavigableString))]
                cn_res = "".join([str(s) for s in nxt]).strip()

        jp_f, cn_f = clean_text(jp_res), clean_text(cn_res)
        if jp_f and cn_f:
            all_skills[jp_f] = cn_f

    browser.close()

# 儲存
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"\n完成！成功攞到 {len(all_skills)} 個技能。")
