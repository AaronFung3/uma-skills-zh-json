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

# 限定條件表 - 純文字模式
print("處理限定條件表...")
found_condition = False
condition_keywords = ["出現兩個或以上限定條件時", "兩個條件都要附合", "先行・長距離", "中距離/長距離"]

for string in soup.find_all(string=True):
    str_text = string.strip()
    if any(kw in str_text for kw in condition_keywords):
        found_condition = True
        print(f"找到限定關鍵句: {str_text[:80]}...")
        
        # 從該 string 開始，向下收集文字行，直到下一個大標題或空
        current = string.parent.next_sibling
        while current:
            if isinstance(current, Tag):
                if current.name in ['h1', 'h2', 'h3', 'p'] and len(current.get_text(strip=True)) > 20:
                    break  # 遇大標題 stop
                text_lines = current.get_text(separator='\n', strip=True).split('\n')
                for line in text_lines:
                    line = line.strip()
                    if '・' in line or '/' in line:
                        # 解析 ・ 或 / 前後
                        if '・' in line:
                            parts = line.split('・', 1)
                        elif '/' in line:
                            parts = line.split('/', 1)
                        else:
                            continue
                        jp = parts[0].strip()
                        cn = parts[1].strip() if len(parts) > 1 else ''
                        jp_clean = clean_text(jp)
                        cn_clean = clean_text(cn)
                        if jp_clean and cn_clean:
                            all_skills[jp_clean] = cn_clean
                            print(f"限定插入: {jp_clean} → {cn_clean} (原行: {line[:50]})")
            current = current.next_sibling if hasattr(current, 'next_sibling') else None
        break

# 固有技能 - 純文字 + td 模式
print("處理固有技能...")
found_unique = False
unique_keywords = ["符合繼承固有的進化條件時直接進化無需選擇", "設定, 符合繼承固有的進化條件時"]

for string in soup.find_all(string=True):
    str_text = string.strip()
    if any(kw in str_text for kw in unique_keywords):
        found_unique = True
        print(f"找到固有關鍵句: {str_text[:80]}...")
        
        current = string.parent.next_sibling
        while current:
            if isinstance(current, Tag):
                if current.name == 'td' and current.get_text(strip=True):
                    td = current
                    text = td.get_text(separator="|", strip=True)
                    jp = ""
                    cn = ""
                    
                    if '/' in text:
                        parts = text.split('/', 1)
                        jp = parts[0].strip()
                        cn = parts[1].strip()
                    else:
                        br = td.find('br')
                        if br:
                            jp = ''.join(str(s).strip() for s in br.previous_siblings if isinstance(s, NavigableString))
                            cn = ''.join(str(s).strip() for s in br.next_siblings if isinstance(s, NavigableString))
                    
                    jp_clean = clean_text(jp)
                    cn_clean = clean_text(cn)
                    if jp_clean and cn_clean:
                        all_skills[jp_clean] = cn_clean
                        print(f"固有插入: {jp_clean} → {cn_clean} (原jp: {jp})")
                if current.name in ['h1', 'h2', 'h3'] and len(current.get_text(strip=True)) > 20:
                    break  # 遇大標題 stop
            current = current.next_sibling if hasattr(current, 'next_sibling') else None
        break

# 寫入
with open('skills.json', 'w', encoding='utf-8') as f:
    json.dump(all_skills, f, ensure_ascii=False, indent=2)

print(f"總共抓取 {len(all_skills)} 個技能，已寫入 skills.json")
