#!/bin/bash
# VUE — install / update on an LG webOS TV from a Mac.
# Run in Terminal:   bash <(curl -fsSL https://vue-tv.github.io/install-lg-mac.sh)
# Needs: the TV and the Mac on the same Wi-Fi, and the LG "Developer Mode" app on the TV
# with "Dev Mode Status" and "Key Server" switched ON.
set -uo pipefail
DEVICE="${WEBOS_DEVICE:-vue-tv}"
IPK_URL="https://vue-tv.github.io/downloads/VUE-LG-webOS-latest.ipk"
APP_ID="sa.tlfzyonk.general"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
export PATH="$HOME/.webos-cli/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

say()  { printf '\n\033[1m%s\033[0m\n' "$1"; }
fail() { printf '\n\033[31mتعذّر الإكمال: %s\033[0m\n' "$1"; exit 1; }

say "VUE · تثبيت على تلفزيون LG"

# 1) webOS tools (once)
if ! command -v ares-install >/dev/null 2>&1; then
  command -v npm >/dev/null 2>&1 || fail "ثبّت Node.js (LTS) من nodejs.org ثم أعد تشغيل هذا الأمر."
  say "تثبيت أدوات LG للمرة الأولى (دقيقة تقريبًا)…"
  npm install --global --prefix "$HOME/.webos-cli" @webos-tools/cli@3 >/dev/null || fail "فشل تثبيت أدوات LG. تأكد من الإنترنت."
fi

# 2) TV definition (once)
if ! ares-setup-device --list 2>/dev/null | awk -v d="$DEVICE" '$1==d{f=1} END{exit !f}'; then
  say "أول مرة: عرّف التلفزيون"
  read -r -p "اكتب IP Address (wireless) الظاهر في تطبيق Developer Mode: " TV_IP </dev/tty
  [[ "$TV_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "العنوان غير صحيح (مثال: 192.168.1.20)."
  ares-setup-device --add "$DEVICE" -i "username=prisoner" -i "host=$TV_IP" -i "port=9922" >/dev/null || fail "تعذر تعريف التلفزيون."
  say "الآن اكتب Passphrase الظاهرة في تطبيق Developer Mode عندما تُطلب:"
  ares-novacom --device "$DEVICE" --getkey </dev/tty || fail "تعذر جلب مفتاح التلفزيون. تأكد أن Key Server مفعّل."
fi

# 3) download latest VUE
say "تنزيل أحدث نسخة من VUE…"
curl -fsSL "$IPK_URL" -o "$WORK/VUE.ipk" || fail "تعذر تنزيل الحزمة."

# 4) install + launch (retry once with a fresh key)
say "تثبيت VUE على التلفزيون…"
if ! ares-install --device "$DEVICE" "$WORK/VUE.ipk"; then
  say "يبدو أن مفتاح التلفزيون تغيّر. اكتب Passphrase الظاهرة في Developer Mode:"
  ares-novacom --device "$DEVICE" --getkey </dev/tty || fail "تعذر جلب المفتاح. تأكد أن Key Server مفعّل وأن التلفزيون على نفس الشبكة."
  ares-install --device "$DEVICE" "$WORK/VUE.ipk" || fail "تعذر التثبيت. تأكد أن Dev Mode Status مفعّل وأن مدة الجلسة لم تنتهِ."
fi
# 5) remove old VUE apps from the first versions (they also show as "VUE" on the TV)
for OLD in sa.tlfzyonk.home sa.tlfzyonk.sport com.tlfzyonk.vue; do
  if ares-install --device "$DEVICE" --list 2>/dev/null | grep -q "^$OLD"; then
    say "حذف نسخة VUE القديمة ($OLD)…"; ares-install --device "$DEVICE" --remove "$OLD" >/dev/null 2>&1 || true
  fi
done
ares-launch --device "$DEVICE" "$APP_ID" >/dev/null 2>&1 || true

say "تم ✓  VUE مثبت ويعمل على التلفزيون."
echo "تذكير: مدة وضع المطوّر تظهر في تطبيق Developer Mode — اضغط Extend Session Time قبل انتهائها."
