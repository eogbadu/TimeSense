#!/usr/bin/env bash
#
# Archive, export and (optionally) upload the iOS app to TestFlight.
#
# The point of this script is that a build is a command, not a sequence of Xcode clicks: the same
# build number, the same export options, the same answers, every time.
#
#   scripts/testflight_build.sh                 # archive + export a signed .ipa
#   scripts/testflight_build.sh --upload        # ...and send it to App Store Connect
#   BUILD_NUMBER=7 scripts/testflight_build.sh  # pin the build number instead of deriving one
#
# Uploading needs an App Store Connect API key (App Manager role or better). Create one at
# App Store Connect → Users and Access → Integrations → App Store Connect API, download the .p8
# ONCE, and put it where xcodebuild looks for it:
#
#   mkdir -p ~/.appstoreconnect/private_keys
#   mv ~/Downloads/AuthKey_XXXXXXXXXX.p8 ~/.appstoreconnect/private_keys/
#
# then export the three values it prints next to the key:
#
#   export ASC_KEY_ID=XXXXXXXXXX
#   export ASC_ISSUER_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
#
# The same key lets -allowProvisioningUpdates mint the Apple Distribution certificate on its own,
# which is why an upload run needs no manual certificate work.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$REPO_ROOT/ios/TimeSense.xcodeproj"
SCHEME="TimeSense"
EXPORT_OPTIONS="$REPO_ROOT/ios/ExportOptions.plist"
BUILD_DIR="${BUILD_DIR:-$REPO_ROOT/build/testflight}"
ARCHIVE="$BUILD_DIR/TimeSense.xcarchive"
EXPORT_DIR="$BUILD_DIR/export"
IPA="$EXPORT_DIR/TimeSense.ipa"

UPLOAD=0
[[ "${1:-}" == "--upload" ]] && UPLOAD=1

# App Store Connect rejects a build number it has seen before for this version, so the default is
# monotonic: seconds since 2026-01-01, which stays inside the 32-bit range for ~68 years and always
# increases. Override with BUILD_NUMBER for a deliberate, readable number.
BUILD_NUMBER="${BUILD_NUMBER:-$(( $(date +%s) - 1767225600 ))}"

echo "==> TimeSense TestFlight build"
echo "    build number : $BUILD_NUMBER"
echo "    output       : $BUILD_DIR"

# An upload needs credentials; find out now rather than after a ten-minute archive.
# Left empty for a non-upload run. macOS ships bash 3.2, where an empty array counts as unset under
# `set -u`, so every expansion below uses the ${a[@]+"${a[@]}"} guard rather than a bare "${a[@]}".
AUTH_ARGS=()
if [[ $UPLOAD -eq 1 ]]; then
  if [[ -z "${ASC_KEY_ID:-}" || -z "${ASC_ISSUER_ID:-}" ]]; then
    echo "error: --upload needs ASC_KEY_ID and ASC_ISSUER_ID set (see the header of this script)." >&2
    exit 1
  fi
  if ! ls ~/.appstoreconnect/private_keys/AuthKey_"$ASC_KEY_ID".p8 >/dev/null 2>&1; then
    echo "error: ~/.appstoreconnect/private_keys/AuthKey_$ASC_KEY_ID.p8 not found." >&2
    echo "       Download the .p8 from App Store Connect and move it there (it can only be downloaded once)." >&2
    exit 1
  fi
  AUTH_ARGS=(-authenticationKeyID "$ASC_KEY_ID"
             -authenticationKeyIssuerID "$ASC_ISSUER_ID"
             -authenticationKeyPath ~/.appstoreconnect/private_keys/AuthKey_"$ASC_KEY_ID".p8)
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

echo "==> Archiving"
xcodebuild archive \
  -project "$PROJECT" \
  -scheme "$SCHEME" \
  -configuration Release \
  -destination 'generic/platform=iOS' \
  -archivePath "$ARCHIVE" \
  CURRENT_PROJECT_VERSION="$BUILD_NUMBER" \
  -allowProvisioningUpdates \
  ${AUTH_ARGS[@]+"${AUTH_ARGS[@]}"}

# Re-sign for distribution. This is the step that swaps the development identity for an Apple
# Distribution one and drops get-task-allow; an archive on its own is not uploadable.
echo "==> Exporting signed .ipa"
xcodebuild -exportArchive \
  -archivePath "$ARCHIVE" \
  -exportOptionsPlist "$EXPORT_OPTIONS" \
  -exportPath "$EXPORT_DIR" \
  -allowProvisioningUpdates \
  ${AUTH_ARGS[@]+"${AUTH_ARGS[@]}"}

echo "==> Verifying the exported build"
unzip -oq "$IPA" -d "$EXPORT_DIR/unzipped"
APP="$EXPORT_DIR/unzipped/Payload/TimeSense.app"
fail=0
check() {  # check <description> <command...>
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "    ok   $desc"; else echo "    FAIL $desc"; fail=1; fi
}
check "Sign in with Apple entitlement present" \
  bash -c "codesign -d --entitlements - --xml '$APP' 2>/dev/null | grep -q applesignin"
# get-task-allow is PRESENT in a distribution build, set to false — a development build sets it
# true. Grepping for the key name therefore proves nothing; read the value.
check "distribution-signed (get-task-allow is false)" \
  bash -c "codesign -d --entitlements - --xml '$APP' 2>/dev/null > '$EXPORT_DIR/ents.plist'
           v=\$(plutil -extract get-task-allow raw -o - '$EXPORT_DIR/ents.plist' 2>/dev/null || echo false)
           [[ \"\$v\" == false ]]"
check "signed with an Apple Distribution identity" \
  bash -c "codesign -dvvv '$APP' 2>&1 | grep -q 'Authority=Apple Distribution'"
check "export compliance declared" \
  bash -c "plutil -p '$APP/Info.plist' | grep -q ITSAppUsesNonExemptEncryption"
check "app privacy manifest bundled" test -f "$APP/PrivacyInfo.xcprivacy"
check "widget privacy manifest bundled" test -f "$APP/PlugIns/TimeSenseWidgetExtension.appex/PrivacyInfo.xcprivacy"
[[ $fail -eq 0 ]] || { echo "error: the exported build failed its checks; not uploading." >&2; exit 1; }

echo "==> Built $IPA"

if [[ $UPLOAD -eq 1 ]]; then
  echo "==> Uploading to App Store Connect"
  xcrun altool --upload-app -f "$IPA" -t ios \
    --apiKey "$ASC_KEY_ID" --apiIssuer "$ASC_ISSUER_ID"
  echo "==> Uploaded. Processing usually takes 5-15 minutes before the build appears in TestFlight."
else
  echo "    Re-run with --upload to send it to TestFlight, or drag the .ipa into Transporter."
fi
