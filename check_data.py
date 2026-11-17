import pandas as pd
import os
import glob

def find_data_files():
    # 搜尋目錄下的 Excel 和 CSV 檔案
    extensions = ['*.xlsx', '*.csv']
    files = []
    for ext in extensions:
        files.extend(glob.glob(ext))
    return files

def analyze_file(filepath):
    print(f"\n{'='*20}")
    print(f"📊 正在分析: {filepath}")
    print(f"{'='*20}")

    try:
        if filepath.endswith('.xlsx'):
            df = pd.read_excel(filepath)
        else:
            df = pd.read_csv(filepath)
    except Exception as e:
        print(f"❌ 無法讀取檔案: {e}")
        return

    print(f"✅ 檔案讀取成功，共 {len(df)} 筆資料")
    print(f"📋 欄位名稱: {list(df.columns)}")

    # 1. 尋找可能的語言對應欄位 (模糊比對)
    cols = df.columns.str.lower()
    eng_col = next((c for c in df.columns if 'eng' in c.lower()), None)
    kwe_col = next((c for c in df.columns if 'kwe' in c.lower() or 'patwa' in c.lower()), None)
    
    # 2. 尋找例句欄位 (這對 AI 訓練最重要)
    eng_ex_col = next((c for c in df.columns if 'example' in c.lower() and 'eng' in c.lower()), None)
    kwe_ex_col = next((c for c in df.columns if 'example' in c.lower() and ('kwe' in c.lower() or 'patwa' in c.lower())), None)

    # --- 分析報告 ---
    
    # A. 單字/詞條層級
    if eng_col and kwe_col:
        print(f"\n🔹 [詞彙庫檢測]")
        print(f"   - 英文欄位: {eng_col}")
        print(f"   - 克語欄位: {kwe_col}")
        
        # 移除空值後的有效配對
        valid_pairs = df[[eng_col, kwe_col]].dropna()
        print(f"   - 有效詞條配對: {len(valid_pairs)} 組")
        
        # 檢查重複
        duplicates = valid_pairs.duplicated().sum()
        if duplicates > 0:
            print(f"   - ⚠️ 發現 {duplicates} 筆重複資料 (建議清理)")
    else:
        print("\n🔸 未偵測到明顯的 英/克 詞彙對應欄位。")

    # B. 例句層級 (AI 訓練的核心)
    if eng_ex_col and kwe_ex_col:
        print(f"\n🔹 [AI 訓練數據 - 例句檢測] (最重要的部分！)")
        print(f"   - 英文例句: {eng_ex_col}")
        print(f"   - 克語例句: {kwe_ex_col}")
        
        # 嚴格篩選：兩邊都要有字，且長度大於 10 (過濾掉只有單字的假例句)
        ex_df = df[[eng_ex_col, kwe_ex_col]].dropna()
        ex_df = ex_df[ex_df[eng_ex_col].astype(str).str.len() > 10]
        
        count = len(ex_df)
        print(f"   - 🔥 高品質訓練句型: {count} 組")
        
        if count < 100:
            print("   👉 評估: 資料量偏少，Fine-tuning 效果不明顯。建議增加到 500+ 組。")
        elif count < 1000:
            print("   👉 評估: 資料量尚可，可以嘗試微調，會有初步效果。")
        else:
            print("   👉 評估: 資料量充足！這非常適合用來訓練模型。")
            
        # 顯示前 3 筆範例
        if count > 0:
            print("\n   [數據預覽]")
            for i in range(min(3, count)):
                print(f"   {i+1}. {ex_df.iloc[i][eng_ex_col]} <-> {ex_df.iloc[i][kwe_ex_col]}")
    else:
        print("\n🔸 未偵測到成對的「例句」欄位。")
        print("   (若要訓練 AI 翻譯長句，強烈建議在 Excel 中整理出 sentence pairs)")

    print("\n------------------------------------------------")

if __name__ == "__main__":
    print("🔍 開始掃描資料夾...")
    files = find_data_files()
    
    if not files:
        print("❌ 找不到 .xlsx 或 .csv 檔案。請確認資料檔是否在同一目錄下。")
    else:
        for f in files:
            analyze_file(f)
            
    input("\n按任意鍵結束...")