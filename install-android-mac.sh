#!/bin/bash
# VUE — install on Android TV / Google TV from a Mac and make VUE the Home app
# (so the Home button cannot leave a locked VUE Kids; outside Kids VUE forwards Home to the TV home).
# Run in Terminal:   bash <(curl -fsSL https://vue-tv.github.io/install-android-mac.sh)
# Needs: the TV and the Mac on the same Wi-Fi, and Developer options on the TV
# (Settings > System > About > press "Android TV OS build" 7 times), with
# "Network debugging" or "Wireless debugging" switched ON.
set -uo pipefail
APK_URL="https://vue-tv.github.io/vue.apk"
PKG="com.tlfzyonk.tvhome"
HOME_ACT="$PKG/$PKG.KidsHomeGuard"
TOOLS="$HOME/.vue-adb"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
export PATH="$TOOLS/platform-tools:/opt/homebrew/bin:/usr/local/bin:$PATH"

say()  { printf '\n\033[1m%s\033[0m\n' "$1"; }
fail() { printf '\n\033[31mتعذّر الإكمال: %s\033[0m\n' "$1"; exit 1; }

say "VUE · تثبيت على جهاز Android TV / Google TV"

# 1) Android platform tools (adb), once
if ! command -v adb >/dev/null 2>&1; then
  say "تنزيل أداة أندرويد الرسمية (adb) للمرة الأولى…"
  mkdir -p "$TOOLS"
  curl -fsSL "https://dl.google.com/android/repository/platform-tools-latest-darwin.zip" -o "$WORK/pt.zip" || fail "تعذر تنزيل adb. تأكد من الإنترنت."
  unzip -q -o "$WORK/pt.zip" -d "$TOOLS" || fail "تعذر فك adb."
fi
adb start-server >/dev/null 2>&1

# 2) connect to the TV
connected() { adb devices | awk 'NR>1 && $2=="device"{f=1} END{exit !f}'; }
if ! connected; then
  SAVED="$(cat "$TOOLS/tv-ip" 2>/dev/null || true)"
  read -r -p "اكتب IP الجهاز (الإعدادات ← الشبكة) ${SAVED:+[$SAVED]}: " TV_IP </dev/tty
  TV_IP="${TV_IP:-$SAVED}"
  [[ "$TV_IP" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || fail "العنوان غير صحيح (مثال: 192.168.1.30)."
  echo "$TV_IP" > "$TOOLS/tv-ip"
  say "الاتصال بالجهاز… (إذا ظهر على التلفزيون طلب «السماح بتصحيح الأخطاء» اختر سماح دائماً)"
  adb connect "$TV_IP:5555" >/dev/null 2>&1; sleep 3
  if ! connected; then
    say "Google TV: افتح «تصحيح الأخطاء اللاسلكي» ← «إقران الجهاز برمز إقران» على التلفزيون."
    read -r -p "اكتب IP:المنفذ الظاهر تحت رمز الإقران (مثال 192.168.1.30:41235): " PAIR </dev/tty
    read -r -p "اكتب رمز الإقران (6 أرقام): " CODE </dev/tty
    adb pair "$PAIR" "$CODE" || fail "فشل الإقران. تأكد من الرمز والمنفذ."
    read -r -p "اكتب IP:المنفذ الظاهر في شاشة «تصحيح الأخطاء اللاسلكي» نفسها (غير منفذ الإقران): " CONN </dev/tty
    adb connect "$CONN" >/dev/null 2>&1; sleep 3
    connected || fail "تعذر الاتصال. تأكد أن الجهاز والكمبيوتر على نفس الشبكة."
  fi
fi

# 3) install the latest VUE
say "تنزيل وتثبيت أحدث نسخة من VUE…"
curl -fsSL "$APK_URL" -o "$WORK/VUE.apk" || fail "تعذر تنزيل VUE."
if ! adb install -r "$WORK/VUE.apk" >"$WORK/install.log" 2>&1; then
  if grep -qi "INSTALL_FAILED_UPDATE_INCOMPATIBLE\|signatures do not match" "$WORK/install.log"; then
    say "نسخة قديمة بتوقيع مختلف — حذفها ثم التثبيت…"
    adb uninstall "$PKG" >/dev/null 2>&1
    adb install "$WORK/VUE.apk" >"$WORK/install.log" 2>&1 || { cat "$WORK/install.log"; fail "تعذر التثبيت."; }
  else
    cat "$WORK/install.log"; fail "تعذر التثبيت."
  fi
fi

# 4) VUE as the Home app
say "جعل VUE تطبيق الهوم…"
adb shell pm enable "$HOME_ACT" >/dev/null 2>&1
adb shell cmd package set-home-activity "$HOME_ACT" >/dev/null 2>&1
NOW="$(adb shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME 2>/dev/null | tail -1 | tr -d '\r')"
adb shell monkey -p "$PKG" -c android.intent.category.LEANBACK_LAUNCHER 1 >/dev/null 2>&1 || true

if [[ "$NOW" == "$PKG/"* ]]; then
  say "تم ✓  VUE مثبت وهو تطبيق الهوم."
  echo "داخل عالم الأطفال والقفل مفعّل: زر الهوم يطلب الرمز السري. وبرا عالم الأطفال: زر الهوم يوديك للشاشة الرئيسية كالعادة."
else
  say "VUE مثبت ✓ لكن الجهاز رفض تغيير تطبيق الهوم (الحالي: ${NOW:-غير معروف})."
  echo "بعض أجهزة Google TV لا تسمح بذلك. استخدم «ملف طفل» من إعدادات Google TV بدلاً منه."
fi
