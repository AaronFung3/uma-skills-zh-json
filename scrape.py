from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, NavigableString
import json
import re

# 直接抓取內容所在的子頁面
url = "https://www.wpstud.com/UmaMusume/UmaAbility_c.htm"

def clean_text(t):
    if not t: return ''
    # 移除所有符號 (◯◎○★... 以及 / 和 ・)
    t = re.sub(r'[◯◎○□△★◇◆☆◼︎▽▲▼△○◎◇◆★☆□△◇◆◯/・/]+', '', t)
    # 移除括號內的數值或註解 (例如 1.2s, 180バ, [バ])
    t = re.sub(r'\(.*?\)|【.*?】|\[.*?\]|\{.*?\}', '', t)
    # 移除剩餘的數字與單位
    t = re.sub(r'\d+\.?\d*[バPt%s]+', '', t)
    return t.strip()

all_skills = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    print("正在載入頁面...")
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    browser.close()

# ====================
# 第一部分：一般技能 (限定條件)
# ====================
print("--- 正在提取：一般技能 ---")
# 搵嗰句長到嘔嘅說明文字
limit_trigger = None
for p in soup.find_all(string=re.compile("出現兩個或以上限定條件時中間顯示")):
    limit_trigger = p
    break

if limit_trigger:
    # 搵呢句嘢之後第一個 table
    table = limit_trigger.find_parent().find_next('table')
    if table:
        rows = table.find_all('tr')[1:] # Skip title
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                # 檢查第二格有無中文
                cn_raw = cells[1].get_text(strip=True)
                if cn_raw:
                    jp_name = clean_text(cells[0].get_text())
                    cn_name = clean_text(cn_raw)
                    if jp_name and cn_name:
                        all_skills[jp_name] = cn_name
        print(f"成功！目前技能總數: {len(all_skills)}")

# ====================
# 第二部分：固有技能
# ====================
print("--- 正在提取：固有技能 ---")
unique_trigger = None
for p in soup.find_all(string=re.compile("符合繼承固有的進化條件時直接進化無需選擇")):
    unique_trigger = p
    break

if unique_trigger:
    # 從這句之後開始搵所有 table
    # 注意：固有技能係分開咗好多個細 table 擺
    current_node = unique_trigger.find_parent()
    while current_node:
        # 如果見到下一部分嘅標題就停 (例如 "一般技能" 大字)
        if current_node.name == 'p' and ("一般技能" in current_node.get_text() or "主動技能" in current_node.get_text()):
             # 確保唔係岩岩開始嗰句
             if "符合繼承固有" not in current_node.get_text():
                break

        if current_node.name == 'table':
            for row in current_node.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 2: continue
                
                target_td = cells[1] # 只睇第二格
                classes = target_td.get('class', [])
                
                jp_res, cn_res = "", ""
                
                # 邏輯 A: 有 forth class 用 / 分
                if 'forth' in classes:
                    txt = target_td.get_text(strip=True)
                    if '/' in txt:
                        parts = txt.split('/', 1)
                        jp_res, cn_res = parts[0], parts[1]
                
                # 邏輯 B: 冇 forth 或者有 br 用 br 分
                else:
                    br = target_td.find('br')
                    if br:
                        # 攞 br 前後嘅純文字
                        # previous_siblings 會倒序，所以要 reversed
                        prev = [s for s in br.previous_siblings if isinstance(s, (str, NavigableString))]
                        jp_res = "".join(reversed([str(s) for s in prev])).strip()
                        
                        nxt = [s for s in br.next_siblings if isinstance(s, (str, NavigableString))]
                        cn_res = "".join([str(s) for s in nxt]).strip()

                jp_f = clean_text(jp_res)
                cn_f = clean_text(cn_res)
                if jp_f and cn_f:
                    all_skills[jp_f] = cn_f

        current_node = current_node.next_sibling

# 寫入 JSON
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"完成！總共抓取 {len(all_skills)} 個技能。已儲存至 skills.json")
