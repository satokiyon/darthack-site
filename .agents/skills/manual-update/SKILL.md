---
name: manual-update
description: >-
  Use this skill when updating the DartHack Japanese/English user manuals in
  darthack-site, re-capturing Android screenshots on Pixel_9a or Small_Tablet,
  updating annotations/{ja,en}.json, or regenerating manual.html and manual_en.html.
---

# DartHack Manual Update & Screenshot Workflow

## 1. Build Release APK (No DEBUG Ribbon)
Always capture manual screenshots using a **Release** build so the red `DEBUG` banner does not appear:

```powershell
powershell -ExecutionPolicy Bypass -File c:\Users\satok\DartHack_private\build_files\android_build.ps1 -Target APK -Mode Release
```

- Built APK location: `C:\Users\satok\DartHack_private\dist\app-release.apk` (fallback: `C:\Users\satok\DartHack\sys\flutter\build\app\outputs\flutter-apk\app-release.apk`).

## 2. Target Virtual Machines (AVDs)
Always use the standard AVDs so screenshot resolutions match `annotations/{ja,en}.json`:
- **Phone (Portrait, `1080x2424`)**: `Pixel_9a` (used for all standard manual screenshots)
- **Tablet (Landscape, `1920x1200`)**: `Small_Tablet` (used for `20_tablet_layout_compare.png`)
- Check available AVDs with: `& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -list-avds`

## 3. Start Emulator & Install APK Cleanly
1. Launch the target AVD (`Pixel_9a` or `Small_Tablet`) as a daemon:
   `& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd Pixel_9a -no-snapshot-save -no-audio`
2. Wait for boot:
   `python scripts/adb_helper.py --serial emulator-5554 wait-boot`
3. Install APK (if `INSTALL_FAILED_UPDATE_INCOMPATIBLE` occurs, run `adb -s emulator-5554 uninstall jp.satokiyo.darthack` first).
4. Force-stop before launching (`adb -s emulator-5554 shell am force-stop jp.satokiyo.darthack`) so old snapshot dialogs do not linger, then wait ~10–15s on first launch for asset extraction (`Preparing assets...`).

## 4. Capture JA & EN Screenshots
- Always pass `--serial emulator-5554` to `adb_helper.py` / `adb` when another device is attached.
- **Drawer Menu**: Do NOT edge-swipe from `x=10..60` (triggers Android Back gesture / Exit dialog). Tap the on-screen hamburger icon (`≡`) instead.
- **Long Settings Sections**: Capture in 2–3 overlapping scroll steps (e.g., `18b`/`18c`/`18d` or `20b`/`20c`/`20d`) so every control is visible without clipping.
- Save raw PNGs to `raw_screenshots/ja/<name>.png` and `raw_screenshots/en/<name>.png`.
- Stop the emulator when finished: `adb -s emulator-5554 emu kill`.

## 5. Annotate, Regenerate HTML, and Verify
- **Settings Order Check**: When adding or reordering settings sections, verify the order in `c:\Users\satok\DartHack\sys\flutter\lib\settings_page.dart` (`ListView` children) so chapters (10–18) and subsections match the actual Game Settings screen order.
1. Update `annotations/ja.json` and `annotations/en.json`.
2. Run:
   ```powershell
   python scripts/annotate_screenshots.py
   python scripts/generate_manual.py
   python scripts/generate_manual.py --check
   ```
3. Visually inspect every newly generated `images/manual/{ja,en}/<name>.png` to confirm box alignment and badge placement.
