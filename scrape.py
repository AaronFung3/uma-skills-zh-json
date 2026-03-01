from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import json
import time

url = "https://wiki.biligame.com/umamusume/%E6%8A%80%E8%83%BD%E9%80%9F%E6%9F%A5%E8%A1%A8"

skills = {}

with sync_playwright() as p:
    # Launch browser with CI-friendly args
    browser = p.chromium.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--disable-extensions'
        ]
    )
    
    page = browser.new_page(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    
    max_retries = 3
    success = False
    
    for attempt in range(max_retries):
        try:
            print(f"嘗試 {attempt + 1}/{max_retries} 載入頁面...")
            page.goto(url, wait_until="domcontentloaded", timeout=90000)
            
            # 等表格出現
            page.wait_for_selector('#CardSelectTr', state="visible", timeout=60000)
            
            # 多等一陣確保內容 render 完
            page.wait_for_timeout(5000)
            
            html = page.content()
            print("頁面標題：", page.title())
            print("HTML 長度：", len(html))
            print("CardSelectTr 存在？", 'CardSelectTr' in html)
            
            soup = BeautifulSoup(html, 'html.parser')
            
            table = soup.find('table', id='CardSelectTr')
            if not table:
                raise Exception("找不到 id='CardSelectTr' 的表格")
            
            rows = table.select('tbody tr')
            print(f"找到 {len(rows)} 行資料")
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue
                
                jp = cells[1].get_text(strip=True)  # 第2個 td: 日文名
                cn = cells[3].get_text(strip=True)  # 第4個 td: 繁中名
                
                if jp and jp.strip():
                    skills[jp] = cn  # 只存繁中名，唔加描述
            
            success = True
            break
            
        except Exception as e:
            print(f"嘗試 {attempt + 1} 失敗: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5)
            else:
                raise
    
    browser.close()

# 寫入 JSON
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(skills, f, ensure_ascii=False, indent=2)

print(f"成功抓取 {len(skills)} 個技能，已寫入 skills.json")
