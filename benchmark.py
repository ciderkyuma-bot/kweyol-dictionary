import pandas as pd
from main import load_databases, run_lego_translation, normalize_text
import time

def calculate_accuracy(pred, truth):
    """計算兩個句子的相似度 (簡單版：看有多少字重疊)"""
    pred_words = set(normalize_text(pred).split())
    truth_words = set(normalize_text(truth).split())
    
    if not truth_words: return 0.0
    
    # 計算交集 (共同的字)
    common = pred_words.intersection(truth_words)
    return len(common) / len(truth_words)

def run_benchmark():
    print("🚀 正在啟動效能評測 (Benchmark)...")
    
    # 1. 載入資料庫
    databases = load_databases()
    df = databases['k2e_data']
    
    if df.empty:
        print("❌ 錯誤：找不到 k2e.csv 資料！")
        return

    print(f"📂 資料庫共有 {len(df)} 句，我們隨機抽測 100 句來跑分...\n")
    
    # 2. 隨機抽樣 100 句 (避免跑太久)
    sample_df = df.sample(n=100, random_state=42) 
    
    total_score = 0
    perfect_matches = 0
    start_time = time.time()

    print(f"{'英文 (Input)':<40} | {'系統翻譯 (System)':<30} | {'標準答案 (Truth)':<30} | {'分數'}")
    print("-" * 120)

    for _, row in sample_df.iterrows():
        english = str(row['English_Example'])
        truth = str(row['Kweyol_Example'])
        
        # 跑翻譯
        system_output = run_lego_translation(english, databases)
        
        # 算分數 (0.0 ~ 1.0)
        score = calculate_accuracy(system_output, truth)
        total_score += score
        
        # 判定是否完美 (或是極高分)
        if score >= 0.8: perfect_matches += 1
        
        # 顯示前 10 句就好，不然螢幕會爆掉
        if _ < 10: 
            print(f"{english[:38]:<40} | {system_output[:28]:<30} | {truth[:28]:<30} | {score:.2f}")

    # 3. 總結報告
    avg_score = (total_score / 100) * 100
    duration = time.time() - start_time
    
    print("-" * 120)
    print(f"\n📊 評測結果報告：")
    print(f"   - 測試句數: 100 句")
    print(f"   - 平均相似度: {avg_score:.1f}% (越高越好)")
    print(f"   - 高準確句數: {perfect_matches} 句 (相似度 > 80%)")
    print(f"   - 總耗時: {duration:.2f} 秒")
    
    if avg_score > 50:
        print("\n🏆 評語：表現不錯！核心單字和結構大多能對應上。")
    else:
        print("\n🔧 評語：還有進步空間，可能是長句子的語序規則還不夠多。")

if __name__ == "__main__":
    run_benchmark()