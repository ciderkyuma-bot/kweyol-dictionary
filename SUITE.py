from main import load_databases, run_lego_translation
import pandas as pd

def run_tests():
    print("🚀 正在啟動自動驗證系統...\n")
    
    # 1. 載入資料庫
    databases = load_databases()
    
    # 2. 定義測試案例 (您可以隨時在這裡增加新句子)
    test_cases = [
        # (類別, 英文輸入, 預期包含的關鍵字)
        ("Tense: Future", "I will go", ["kay", "alé"]),
        ("Tense: Progressive", "I am eating", ["ka", "manjé"]),
        ("Tense: Past", "I was eating", ["té", "ka", "manjé"]),
        ("Tense: Perfect", "I have eaten", ["ja", "manjé"]),
        ("Negation", "I don't know", ["pa"]),
        ("Copula (Is)", "He is a cook", ["sé", "kwizinyé"]),
        ("Stative Verb", "I want it", ["vlé"]), # 確保沒有 ka
        ("Pattern: Possessive", "My father", ["papa", "mwen"]),
        ("Pattern: Article", "The book", ["liv", "la"]),
    ]
    
    score = 0
    total = len(test_cases)
    
    # 3. 開始測試
    for category, input_text, expected_keywords in test_cases:
        # 執行翻譯
        output = run_lego_translation(input_text, databases)
        
        # 檢查是否包含所有關鍵字
        passed = True
        missing = []
        for kw in expected_keywords:
            if kw.lower() not in output.lower():
                passed = False
                missing.append(kw)
        
        # 特殊檢查：狀態動詞不應該有 ka
        if category == "Stative Verb" and "ka " in output.lower():
            passed = False
            missing.append("NO 'ka'")

        # 顯示結果
        if passed:
            print(f"✅ [{category}] PASS")
            score += 1
        else:
            print(f"❌ [{category}] FAIL")
            print(f"   Input:    {input_text}")
            print(f"   Output:   {output}")
            print(f"   Missing:  {missing}")
        print("-" * 30)

    # 4. 總結
    print(f"\n📊 測試報告: 通過 {score}/{total} (準確率: {score/total*100:.1f}%)")
    
    if score == total:
        print("🏆 恭喜！系統核心邏輯運作正常！")
    else:
        print("🔧 請針對 FAIL 的項目檢查 grammar.csv 或 patterns.csv")

if __name__ == "__main__":
    run_tests()