#!/usr/bin/env bash
# 릴스 분석 도구 설치 스크립트 (macOS)
# - Homebrew (없으면 설치, 맥 비밀번호 필요)
# - yt-dlp, ffmpeg, whisper-cpp
# - whisper 모델 ggml-large-v3-turbo-q5_0.bin -> ~/.cache/whisper
set -euo pipefail

MODEL_NAME="ggml-large-v3-turbo-q5_0.bin"
MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/${MODEL_NAME}"
MODEL_DIR="${HOME}/.cache/whisper"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "이 스크립트는 macOS용입니다." >&2
  exit 1
fi

# 1. Homebrew
if ! command -v brew >/dev/null 2>&1; then
  for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do
    [[ -x "$p" ]] && eval "$("$p" shellenv)" && break
  done
fi
if ! command -v brew >/dev/null 2>&1; then
  echo "==> Homebrew 설치 (맥 비밀번호를 물어보면 입력하세요)"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  if [[ -x /opt/homebrew/bin/brew ]]; then
    BREW=/opt/homebrew/bin/brew
  else
    BREW=/usr/local/bin/brew
  fi
  eval "$("$BREW" shellenv)"
  # 새 터미널에서도 brew를 쓸 수 있게 등록
  if ! grep -q 'brew shellenv' "${HOME}/.zprofile" 2>/dev/null; then
    echo "eval \"\$(${BREW} shellenv)\"" >> "${HOME}/.zprofile"
  fi
fi

# 2. 도구 설치
echo "==> yt-dlp, ffmpeg, whisper.cpp 설치"
brew install yt-dlp ffmpeg whisper.cpp

# 3. whisper 모델
mkdir -p "$MODEL_DIR"
if [[ -s "${MODEL_DIR}/${MODEL_NAME}" ]]; then
  echo "==> 모델이 이미 있습니다: ${MODEL_DIR}/${MODEL_NAME}"
else
  echo "==> whisper 모델 다운로드 (약 550MB)"
  curl -L --fail -C - -o "${MODEL_DIR}/${MODEL_NAME}.part" "$MODEL_URL"
  mv "${MODEL_DIR}/${MODEL_NAME}.part" "${MODEL_DIR}/${MODEL_NAME}"
fi

# 4. 버전 확인
echo
echo "==> 설치된 버전"
echo "brew:        $(brew --version | head -1)"
echo "yt-dlp:      $(yt-dlp --version)"
echo "ffmpeg:      $(ffmpeg -version | head -1)"
if command -v whisper-cli >/dev/null 2>&1; then
  echo "whisper-cli: $(command -v whisper-cli) ($(brew list --versions whisper.cpp))"
else
  echo "whisper-cli: 찾을 수 없음 - 새 터미널을 열고 다시 확인하세요" >&2
  exit 1
fi
ls -lh "${MODEL_DIR}/${MODEL_NAME}"
echo
echo "설치 끝!"
