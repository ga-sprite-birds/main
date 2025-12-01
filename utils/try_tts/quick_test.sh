#!/bin/bash

source conda-init && conda activate ga-sprite-birds

echo "列出中文音色："
python utils/try_tts/cli.py list --language zh-CN

echo ""
echo "生成试听音频："
python utils/try_tts/cli.py generate --voice zh-CN-XiaoxiaoNeural

