# ====================
# 第二部分：固有技能 - 最尾個 table
# ====================
print("--- 處理固有技能 (最尾 table) ---")
unique_table = all_tables[-1]
rows = unique_table.find_all('tr')[1:]  # 跳過第一個 tr
for row in rows:
    cells = row.find_all('td')
    if len(cells) < 2:
        continue
    
    # 優先讀第一格作為日文
    jp_cell = cells[0]
    cn_cell = cells[1]
    
    jp_raw = jp_cell.get_text(strip=True)
    cn_raw = cn_cell.get_text(strip=True)
    
    # 如果第一格冇內容或太短（例如只係符號/空），改讀第二格
    if not jp_raw or len(jp_raw) < 5 or not re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]', jp_raw):
        jp_raw = cn_raw
        cn_raw = ""  # 第二格變日文，中文冇（或之後再抽）
    
    # 如果第二格有內容，就試分隔日中
    if cn_raw:
        jp_res = jp_raw
        cn_res = cn_raw
        
        # 如果有 / ，分隔
        if '/' in cn_raw:
            parts = cn_raw.split('/', 1)
            jp_res = parts[0].strip()
            cn_res = parts[1].strip()
        else:
            br = cn_cell.find('br')
            if br:
                jp_parts = []
                sib = br.previous_sibling
                while sib:
                    if isinstance(sib, NavigableString):
                        jp_parts.append(sib.strip())
                    sib = sib.previous_sibling
                jp_res = ''.join(reversed(jp_parts)).strip()
                
                cn_parts = []
                sib = br.next_sibling
                while sib:
                    if isinstance(sib, NavigableString):
                        cn_parts.append(sib.strip())
                    if isinstance(sib, Tag) and sib.name == 'br':
                        break
                    sib = sib.next_sibling
                cn_res = ''.join(cn_parts).strip()
    else:
        jp_res = jp_raw
        cn_res = ""
    
    jp_f = clean_text(jp_res)
    cn_f = clean_text(cn_res)
    if jp_f and cn_f:
        all_skills[jp_f] = cn_f
        print(f"固有: {jp_f} → {cn_f} (原jp: {jp_res[:50]})")
    else:
        print("固有 td 無有效日中對應，跳過:", jp_raw[:50] + " | " + cn_raw[:50])
