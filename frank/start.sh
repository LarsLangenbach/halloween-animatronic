#!/bin/zsh
# Start Frank with his web page, microphone on, and open the page once he's up.
# Typing `frank` in a terminal runs this (an alias in ~/.zshrc). Options go through to
# web.py and win over the ones here, e.g.
#     frank --model opus-5.5         a different brain (default sonnet-5.5: 1.5 s to the first sentence, Opus 2.4)
#     frank --speaker "Jar"          his voice through another output (part of its name)
#     frank --mute                   no voice
#     frank --video clip.mp4         a recording instead of the camera
# Ctrl+C stops him.

cd "${0:A:h}/.." || exit 1
(until curl -s -o /dev/null http://localhost:8800/state; do sleep 1; done; open http://localhost:8800) &
exec uv run --no-project --with anthropic --with openai --with httpx --with sounddevice \
    --with numpy --with scipy --with websockets --with livekit --with opencv-python --with mediapipe \
    python frank/web.py --talk --model sonnet-5.5 --speaker "MacBook Pro Speakers" "$@"
