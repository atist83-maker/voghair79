#!/usr/bin/env bash
# '영상편집 자동화' 작업 공간 세팅 (macOS)
# 사용: 이 폴더에서  bash setup-video-workspace.sh
set -uo pipefail
cd "$(dirname "$0")"

say() { printf '\n==> %s\n' "$1"; }

# 0. 운영체제 확인
say "운영체제: $(sw_vers -productName 2>/dev/null) $(sw_vers -productVersion 2>/dev/null) ($(uname -m))"
if [[ "$(uname)" != "Darwin" ]]; then echo "이 스크립트는 macOS용이에요."; exit 1; fi

# Homebrew (맥용 프로그램 설치 도구)
if ! command -v brew >/dev/null 2>&1; then
  for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [[ -x $p ]] && eval "$($p shellenv)" && break; done
fi
if ! command -v brew >/dev/null 2>&1; then
  say "Homebrew 설치: 아래 프로그램들을 설치하는 도구예요 (맥 비밀번호를 물어봐요)"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  for p in /opt/homebrew/bin/brew /usr/local/bin/brew; do [[ -x $p ]] && eval "$($p shellenv)" && break; done
fi

# 1. Python 3.10+, FFmpeg, Node.js 22+
py_ok() { python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; }
if ! py_ok; then
  say "Python 3.12 설치: 자막·편집 자동화 스크립트를 돌리는 언어예요"
  brew install python@3.12
  export PATH="$(brew --prefix python@3.12)/libexec/bin:$PATH"
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  say "FFmpeg 설치: 영상을 자르고 소리를 뽑는 도구예요"
  brew install ffmpeg
fi
node_ok() { command -v node >/dev/null 2>&1 && [[ "$(node -p 'process.versions.node.split(".")[0]')" -ge 22 ]]; }
if ! node_ok; then
  say "Node.js 22 설치: 영상 템플릿 도구(HyperFrames 등)가 쓰는 실행기예요"
  brew install node@22
  export PATH="$(brew --prefix node@22)/bin:$PATH"
fi

# 2. 가상환경 + faster-whisper, pycapcut
if [[ ! -d .venv ]]; then
  say "가상환경(.venv) 만들기: 이 폴더 전용 파이썬 상자라 다른 프로그램과 안 섞여요"
  python3 -m venv .venv
fi
say "faster-whisper(음성→자막), pycapcut(CapCut 초안 자동 생성) 설치"
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

# 3. 폴더
mkdir -p input output

# 4. CapCut 초안 폴더 찾기
DRAFT=""
for d in "$HOME/Movies/CapCut/User Data/Projects/com.lveditor.draft" \
         "$HOME/Library/Containers/com.lemon.lvoverseas/Data/Movies/CapCut/User Data/Projects/com.lveditor.draft"; do
  [[ -d "$d" ]] && DRAFT="$d" && break
done
if [[ -z "$DRAFT" ]]; then
  DRAFT="$(find "$HOME/Movies" "$HOME/Library/Containers" -maxdepth 7 -type d -name 'com.lveditor.draft' 2>/dev/null | head -1)"
fi
[[ -n "$DRAFT" ]] && echo "$DRAFT" > .capcut_draft_path

# 5. 결과표
v() { "$@" 2>/dev/null | head -1; }
PYV=$(v python3 --version); FFV=$(v ffmpeg -version | awk '{print $3}'); NV=$(v node --version)
FW=$(.venv/bin/python -c 'import faster_whisper;print(faster_whisper.__version__)' 2>/dev/null)
PC=$(.venv/bin/pip show pycapcut 2>/dev/null | awk '/^Version/{print $2}')
mark() { [[ -n "$1" ]] && echo "✅" || echo "❌"; }
echo
echo "| 항목 | 상태 | 버전/위치 |"
echo "|---|---|---|"
echo "| Python 3.10+ | $(py_ok && echo ✅ || echo ❌) | $PYV |"
echo "| FFmpeg | $(mark "$FFV") | $FFV |"
echo "| Node.js 22+ | $(node_ok && echo ✅ || echo ❌) | $NV |"
echo "| .venv | $(mark "$([[ -x .venv/bin/python ]] && echo y)") | $(pwd)/.venv |"
echo "| faster-whisper | $(mark "$FW") | $FW |"
echo "| pycapcut | $(mark "$PC") | $PC |"
echo "| input / output | $(mark "$([[ -d input && -d output ]] && echo y)") | $(pwd)/input, output |"
echo "| CapCut 초안 폴더 | $(mark "$DRAFT") | ${DRAFT:-못 찾음 → CapCut 설정에서 확인} |"
