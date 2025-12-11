import fitz  # PyMuPDF
import openpyxl
from io import BytesIO

def get_toc_data(pdf_bytes):
    """
    アップロードされたPDFバイトデータからしおり(TOC)情報を抽出してリストで返す。
    エラー時は空リストを返す。
    """
    try:
        # stream=pdf_bytes でメモリ上のデータを開く
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        toc = doc.get_toc(simple=False)  # [[lvl, title, page, ...], ...]
        doc.close()
        return toc
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return []

def extract_pdf_by_indices(pdf_bytes, selected_indices):
    """
    PDFバイトデータと、選択されたしおりのインデックス(リスト)を受け取り、
    抽出後のPDFバイトデータを返す。
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    toc = doc.get_toc(simple=False)
    
    # 選択されたしおり情報を取得
    selected_toc_items = []
    for idx in selected_indices:
        if 0 <= idx < len(toc):
            selected_toc_items.append(toc[idx])
            
    # ページ番号(item[2])でソートして処理順序を整える
    selected_toc_items.sort(key=lambda x: x[2])

    # 全しおりについて、各しおりが担当する「開始ページ〜終了ページ」を計算
    # (元のコードのロジックを踏襲)
    all_page_ranges = []
    for i in range(len(toc)):
        current_page = toc[i][2] - 1  # 0-based index
        
        # 次のしおりの開始ページの前までを範囲とする
        if i + 1 < len(toc):
            next_page = toc[i + 1][2] - 2
        else:
            next_page = len(doc) - 1
            
        all_page_ranges.append((toc[i], current_page, next_page))

    # 選択されたしおりに対応するページ範囲を抽出
    target_ranges = []
    
    # 選択アイテムと完全に一致する(level, title, page)範囲を探す
    for sel_item in selected_toc_items:
        for range_item, start, end in all_page_ranges:
            # level, title, page が一致するか確認
            if sel_item[:3] == range_item[:3]:
                target_ranges.append((sel_item, start, end))
                break
    
    if not target_ranges:
        doc.close()
        return None

    # 新しいPDFを作成
    new_doc = fitz.open()
    included_pages = []     # 重複ページ防止用
    page_map = {}           # 元のページ番号 -> 新しいPDFのページ番号

    for _, start, end in target_ranges:
        # 範囲内のページを順に追加
        for p in range(start, end + 1):
            if p not in included_pages:
                page_map[p] = len(included_pages) + 1
                included_pages.append(p)
                new_doc.insert_pdf(doc, from_page=p, to_page=p)

    # 抽出後のPDFにしおり情報を再構築
    new_toc = []
    for item, start, _ in target_ranges:
        level, title, _ = item[:3]
        # 元の開始ページに対応する、新しいPDFでのページ番号を取得
        new_page_num = page_map.get(start, 1)
        new_toc.append([level, title, new_page_num])
    
    # しおりをセット
    new_doc.set_toc(new_toc)
    
    # メモリ上にバイトデータとして書き出し
    out_bytes = new_doc.tobytes()
    
    doc.close()
    new_doc.close()
    
    return out_bytes

def create_excel_report(pdf_bytes):
    """
    PDFデータを受け取り、ページ数カウント表のExcelバイトデータを返す。
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    toc = doc.get_toc(simple=False)
    
    # ページ数計算ロジック
    all_page_ranges = []
    for i in range(len(toc)):
        current_page = toc[i][2] - 1
        if i + 1 < len(toc):
            next_page = toc[i + 1][2] - 2
        else:
            next_page = len(doc) - 1
        
        page_count = next_page - current_page + 1
        all_page_ranges.append((toc[i], page_count))
        
    # Excel作成
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # 最大階層を調べてヘッダー作成
    if all_page_ranges:
        max_level = max(t[0][0] for t in all_page_ranges)
    else:
        max_level = 1
        
    headers = [f"Level {i}" for i in range(1, max_level + 1)] + ["ページ数"]
    ws.append(headers)
    
    # データ書き込み
    hierarchy = [""] * max_level
    for toc_item, count in all_page_ranges:
        level, title, _ = toc_item[:3]
        
        # 階層構造の維持
        hierarchy[level - 1] = title
        # 下位階層をクリア
        for j in range(level, max_level):
            hierarchy[j] = ""
            
        ws.append(hierarchy[:] + [count])
        
    # メモリ上に保存
    output = BytesIO()
    wb.save(output)
    doc.close()
    
    return output.getvalue()