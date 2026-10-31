#!/bin/zsh
# Point https://frank-live.vercel.app at a new tunnel address and redeploy.
#     frank/live/point.sh https://<words>.trycloudflare.com
# The quick tunnel gets a new address every time cloudflared restarts. This rewrites
# vercel.json's redirect and deploys this folder (only this folder: never the repository).
set -e
url="${1%/}"
[[ "$url" == https://* ]] || { echo "usage: $0 https://<words>.trycloudflare.com"; exit 1; }
cd "${0:A:h}"
sed -i '' -E "s#\"destination\": \"https://[^/\"]+/\\\$1\"#\"destination\": \"$url/\$1\"#" vercel.json
grep -F "$url" vercel.json >/dev/null || { echo "vercel.json was not rewritten"; exit 1; }
vercel deploy --prod --yes
echo "https://frank-live.vercel.app now forwards to $url"
