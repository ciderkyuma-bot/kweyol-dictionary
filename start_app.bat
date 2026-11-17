@echo off
REM 設定編碼為 UTF-8 以顯示中文
chcp 65001 > nul

REM 設定視窗標題，看起來更專業
title Kwéyòl AI Dictionary Launcher

echo ========================================================
echo   🚀 正在啟動 Kwéyòl AI 字典 (Beta 翻譯版)
echo   包含 NLLB 機器學習模型
echo ========================================================

REM 1. 切換到 .bat 檔案所在的資料夾
cd /d "%~dp0"

echo.
echo [系統] 當前工作目錄:
cd

REM 檢查是否有模型資料夾 (這裡原本的括號會導致崩潰，已修正為中括號)
if exist "local_model" (
    echo [狀態] 檢測到本地 AI 模型 [local_model]，將優先使用。
) else (
    echo [狀態] 未檢測到本地模型，將嘗試從 HuggingFace 下載 [需連網]。
)

echo.
echo [系統] 正在啟動虛擬環境...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else (
    echo [警告] 找不到 .venv 資料夾，嘗試使用全域 Python...
)

REM 驗證 Python 環境 (確認有安裝 AI 套件)
echo.
echo [檢查] 驗證 AI 核心套件...
python -c "import torch; import transformers; print('AI 環境檢測: OK')" || (
    echo [錯誤] 缺少 AI 套件！請確認是否已執行 pip install -r requirements.txt
    pause
    exit
)

echo.
echo ========================================================
echo   正在啟動 Streamlit Server...
echo   請稍候，AI 模型載入可能需要幾秒鐘...
echo ========================================================

REM 2. 執行 Streamlit (指定 Port 8502，避免跟普通版 8501 衝突)
streamlit run streamlit_app.py --server.port 8502

echo.
echo 網站伺服器已關閉。
pause