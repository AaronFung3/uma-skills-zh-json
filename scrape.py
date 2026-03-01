from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, Tag
import json
import re
import time

url = "https://www.wpstud.com/UmaMusume/UmaAbility.htm"

def clean_text(t):
    if not t: return ''
    # 移除符號、括號及其內容
    t = re.sub(r'[◯◎○□△★◇◆☆◼︎▽▲▼△○◎◇◆★☆□△◇◆◯・/]+', '', t)
    t = re.sub(r'\(.*?\)|【.*?】|\[.*?\]|\{.*?\}', '', t)
    # 移除數字和單位 (如 1.2s, 180バ)
    t = re.sub(r'\d+\.?\d*[バPt/～~%]+', '', t)
    return re.sub(r'\s+', '', t).strip()

all_skills = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print(f"正在載入 {url} ...")
    page.goto(url, wait_until="networkidle")
    
    # --- 關鍵修正：處理 Frame ---
    # 檢查是否有 frame，如果有，切換到名為 'main' 的 frame
    content_frame = None
    for frame in page.frames:
        if "main" in frame.name.lower() or "ability" in frame.url.lower():
            content_frame = frame
            break
    
    target = content_frame if content_frame else page
    print(f"正在從 {target.url} 提取內容...")
    
    # 等待表格載入
    target.wait_for_selector("table")
    html = target.content()
    soup = BeautifulSoup(html, 'html.parser')
    browser.close()

# ====================
# 第一部分：限定條件
# ====================
print("--- 處理限定條件表 ---")
# 使用更寬鬆的搜尋，因為網頁編碼可能影響精確比對
limit_p = None
for p_tag in soup.find_all('p'):
    if "出現兩個或以上限定條件" in p_tag.get_text():
        limit_p = p_tag
        break

if limit_p:
    table = limit_p.find_next('table')
    if table:
        for row in table.find_all('tr')[1:]:
            cells = row.find_all('td')
            if len(cells) >= 2:
                cn_raw = cells[1].get_text(strip=True)
                if cn_raw: # 有中文才捉
                    jp_name = clean_text(cells[0].get_text())
                    cn_name = clean_text(cn_raw)
                    if jp_name and cn_name:
                        all_skills[jp_name] = cn_name
                        # print(f"限定: {jp_name} -> {cn_name}")

# ====================
# 第二部分：固有技能
# ====================
print("--- 處理固有技能 ---")
unique_p = None
for p_tag in soup.find_all('p'):
    if "符合繼承固有的進化條件" in p_tag.get_text():
        unique_p = p_tag
        break

if unique_p:
    # 固有技能可能分散在多個 table
    curr = unique_p.find_next()
    while curr:
        if curr.name == 'table':
            for row in curr.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 2: continue
                
                target_td = cells[1]
                classes = target_td.get('class', [])
                
                jp_res, cn_res = "", ""
                
                if 'forth' in classes:
                    txt = target_td.get_text(strip=True)
                    if '/' in txt:
                        parts = txt.split('/')
                        jp_res, cn_res = parts[0], parts[1]
                else:
                    # 處理含有 <br> 的結構
                    br = target_td.find('br')
                    if br:
                        # 提取 br 前後的文字節點
                        prev_nodes = [n for n in br.previous_siblings if isinstance(n, str)]
                        next_nodes = [n for n in br.next_siblings if isinstance(n, str)]
                        jp_res = "".join(reversed(prev_nodes)).strip()
                        cn_res = "".join(next_nodes).strip()
                
                jp_f, cn_f = clean_text(jp_res), clean_text(cn_res)
                if jp_f and cn_f:
                    all_skills[jp_f] = cn_f
        
        # 避免跑過頭，如果遇到下一個大標題就停止（可選）
        if curr.name == 'hr': break 
        curr = curr.next_sibling
        if not curr: break

with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"\n完成！總共抓取 {len(all_skills)} 個技能。")
