import streamlit as st
import pandas as pd
import pdf_logic  # 同じフォルダにある pdf_logic.py をインポート

# --- ページ設定 ---
st.set_page_config(
    page_title="PDFしおり単位抽出ツール (SaaS版)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSSで見た目を少し調整（任意） ---
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- タイトルと説明 ---
st.title("📄 PDFしおり単位抽出ツール (Web版)")
st.markdown("""
このツールはPDFの「しおり（目次）」構造を読み取り、
指定したセクションだけを抽出して新しいPDFを作成したり、ページ数を集計してExcelに出力します。
""")

# --- サイドバー：ファイルアップロード ---
with st.sidebar:
    st.header("1. ファイル選択")
    uploaded_file = st.file_uploader("PDFをドラッグ&ドロップ", type="pdf")
    
    st.info("※ アップロードされたファイルは処理終了後にメモリから破棄されます。")

# --- メイン処理 ---
if uploaded_file is not None:
    # PDFをバイトデータとして読み込み
    pdf_bytes = uploaded_file.getvalue()
    
    # ロジック呼び出し：しおり情報の取得
    toc = pdf_logic.get_toc_data(pdf_bytes)
    
    if not toc:
        st.error("⚠️ このPDFには「しおり（目次）」が含まれていないか、読み込めませんでした。")
    else:
        st.header("2. 抽出したいしおり（目次）を選択")
        
        # --- データフレーム作成 ---
        table_data = []
        for i, item in enumerate(toc):
            level, title, page = item[:3]
            
            # 視認性を良くするためのインデント処理
            indent = "　" * (level - 1)
            marker = "■" if level == 2 else ("●" if level >= 3 else "")
            display_title = f"{indent}{marker} {title}"
            
            table_data.append({
                "抽出": False,          # チェックボックス用列
                "しおり名": display_title,
                "開始ページ": page,
                "original_index": i    # ロジック用の隠し列
            })
            
        df = pd.DataFrame(table_data)
        
        # --- データエディタ（表）の表示 ---
        # ユーザーがチェックボックスを操作できる表を表示
        edited_df = st.data_editor(
            df,
            column_config={
                "抽出": st.column_config.CheckboxColumn(
                    "選択",
                    help="抽出したいしおり（目次）にチェックを入れてください",
                    default=False
                ),
                "original_index": None  # インデックス列は画面には表示しない
            },
            disabled=["セクション名", "開始ページ"], # 編集不可にする列
            hide_index=True,
            use_container_width=True,
            height=500
        )
        
        # --- 操作ボタンエリア ---
        st.header("3. 実行")
        col1, col2 = st.columns(2)
        
        # [PDF抽出ボタン]
        with col1:
            if st.button("選択範囲を抽出してPDF作成", type="primary"):
                # チェックが入っている行をフィルタリング
                selected_rows = edited_df[edited_df["抽出"] == True]
                selected_indices = selected_rows["original_index"].tolist()
                
                if not selected_indices:
                    st.warning("まずは上の表で、抽出したいしおり（目次）にチェックを入れてください。")
                else:
                    with st.spinner("PDFを作成しています..."):
                        # ロジック呼び出し
                        result_pdf = pdf_logic.extract_pdf_by_indices(pdf_bytes, selected_indices)
                        
                        if result_pdf:
                            st.success("✅ 作成完了！")
                            # ダウンロードボタンを表示
                            st.download_button(
                                label="📥 加工済みPDFをダウンロード",
                                data=result_pdf,
                                file_name=f"{uploaded_file.name.replace('.pdf', '')}_extracted.pdf",
                                mime="application/pdf"
                            )
                        else:
                            st.error("PDFの作成に失敗しました。")

        # [Excel出力ボタン]
        with col2:
            if st.button("ページ数一覧をExcel出力"):
                with st.spinner("Excelを作成しています..."):
                    # ロジック呼び出し
                    excel_data = pdf_logic.create_excel_report(pdf_bytes)
                    
                    st.success("✅ 作成完了！")
                    st.download_button(
                        label="📥 Excelをダウンロード",
                        data=excel_data,
                        file_name=f"{uploaded_file.name.replace('.pdf', '')}_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

else:
    # ファイル未選択時の表示

    st.info("👈 左側のサイドバーからPDFファイルをアップロードしてください。")

