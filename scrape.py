from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json

url = "https://wiki.biligame.com/umamusume/%E6%8A%80%E8%83%BD%E9%80%9F%E6%9F%A5%E8%A1%A8"

skills = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto(url, wait_until="networkidle", timeout=60000)
    page.wait_for_selector('#CardSelectTr', timeout=30000)
    
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    
    table = soup.find('table', id='CardSelectTr')
    if not table:
        print("找不到 id='CardSelectTr' 的表格！")
        browser.close()
        exit(1)
    
    rows = table.select('tbody tr')
    print(f"找到 {len(rows)} 行資料")
    
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 4:
            continue  # 跳過不完整的行
        
        # 根據你描述：
        # 第 2 個 td (index 1)：日文技能名
        jp = cells[1].get_text(strip=True)
        
        # 第 4 個 td (index 3)：繁體中文名
        cn = cells[3].get_text(strip=True)
        
        # 效果描述（如果有，通常在第 5 個或之後；這裡假設第 5 個 td 是主要描述）
        desc = ''
        if len(cells) >= 5:
            desc = cells[4].get_text(strip=True)
            # 如果描述分散在多個 td，可以用 ' '.join(c.get_text(strip=True) for c in cells[4:]) 合併
        
        if jp and jp.strip():  # 確保日文名不空
            # 組合格式：你可以調整，例如只用 cn，或加 desc
            value = cn
            if desc:
                value += f"：{desc}"
            
            skills[jp] = value
            
            # debug 輸出（上線可註解）
            # print(f"{jp} → {value}")
    
    browser.close()

# 寫入 JSON
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(skills, f, ensure_ascii=False, indent=2)

print(f"成功抓取 {len(skills)} 個技能，已寫入 skills.json")
