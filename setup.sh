#!/bin/bash

# 建立一個資料夾讓 Streamlit 知道去哪裡找 NLTK 的資料
mkdir -p /home/appuser/.nltk_data/

# 使用 Python 指令下載 'punkt' 和 'wordnet' 到剛剛建立的資料夾中
python -m nltk.downloader -d /home/appuser/.nltk_data/ punkt wordnet