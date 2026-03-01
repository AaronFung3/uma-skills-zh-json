from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup, Tag, NavigableString
import json
import re
import time

url = "https://www.wpstud.com/UmaMusume/UmaAbility.htm"

def clean_text(t):
    if not t:
        return ''
    # 移除所有符號（含圓圈、星號、方格等）
    t = re.sub(r'[◯◎○□△★◇◆☆◼︎▽▲▼△○◎◇◆★☆□△◇◆◯・/]+', '', t)
    # 移除括號內容與剩餘雜質
    t = re.sub(r'\(.*?\)|【.*?】|\[.*?\]|\{.*?\}', '', t)
    # 移除空白
    t = re.sub(r'\s+', '', t).strip()
    return t

all_skills = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    print("正在載入頁面...")
    page.goto(url, wait_until="networkidle", timeout=120000)
    # 給予額外時間讓動態內容或複雜 Table 渲染
    time.sleep(5)
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    browser.close()

# ====================
# 第一部分：限定條件表
# ====================
print("--- 處理限定條件表 ---")
# 關鍵字定位
limit_trigger = soup.find(string=re.compile("出現兩個或以上限定條件時中間顯示"))
if limit_trigger:
    target_p = limit_trigger.find_parent('p')
    table = target_p.find_next('table')
    if table:
        rows = table.find_all('tr')[1:]  # 跳過標題列
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                jp_raw = cells[0].get_text(strip=True)
                cn_raw = cells[1].get_text(strip=True)
                
                # 只有第二格(中文)有內容才處理
                if cn_raw:
                    jp_name = clean_text(jp_raw)
                    cn_name = clean_text(cn_raw)
                    if jp_name and cn_name:
                        all_skills[jp_name] = cn_name
                        print(f"[限定] {jp_name} -> {cn_name}")

# ====================
# 第二部分：固有技能
# ====================
print("\n--- 處理固有技能 ---")
unique_trigger = soup.find(string=re.compile("設定, 符合繼承固有的進化條件時直接進化無需選擇"))
if unique_trigger:
    target_p = unique_trigger.find_parent('p')
    # 固有技能通常在說明文字後的多個 table 中，或者一個大 table 裡
    # 這裡我們找說明文字後的所有 tr，或者直接找之後最近的 table
    table = target_p.find_next('table')
    if table:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            # 根據要求，只看每行的第二個 td (index 1)
            if len(cells) < 2:
                continue
            
            target_td = cells[1]
            td_class = target_td.get('class', [])
            
            jp_res = ""
            cn_res = ""

            if 'forth' in td_class:
                # 邏輯：如果有 /，前面是日文，後面是中文，不理 br
                raw_text = target_td.get_text(strip=True)
                if '/' in raw_text:
                    parts = raw_text.split('/')
                    jp_res = parts[0]
                    cn_res = parts[1]
            else:
                # 邏輯：用 <br> 分，前日後中
                # 使用 content 獲取包含標籤的列表
                contents = list(target_td.contents)
                br_index = -1
                for i, content in enumerate(contents):
                    if isinstance(content, Tag) and content.name == 'br':
                        br_index = i
                        break
                
                if br_index != -1:
                    # 合併 br 之前的文字
                    jp_res = "".join([c.get_text() if isinstance(c, Tag) else str(c) for c in contents[:br_index]]).strip()
                    # 合併 br 之後的文字
                    cn_res = "".join([c.get_text() if isinstance(c, Tag) else str(c) for c in contents[br_index+1:]]).strip()

            # 清理並存檔
            jp_final = clean_text(jp_res)
            cn_final = clean_text(cn_res)
            
            if jp_final and cn_final:
                all_skills[jp_final] = cn_final
                print(f"[固有] {jp_final} -> {cn_final}")

# 儲存結果
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"\n完成！共抓取 {len(all_skills)} 筆資料。")
