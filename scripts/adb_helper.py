#!/usr/bin/env python3
"""
ADB を用いた仮想デバイス操作およびスクリーンショット保存ヘルパー。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def run_adb(args: list[str], serial: str | None = None, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    cmd = ["adb"]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, check=check)


def wait_for_boot(serial: str | None = None, timeout_sec: int = 120) -> None:
    run_adb(["wait-for-device"], serial=serial)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        res = run_adb(["shell", "getprop", "sys.boot_completed"], serial=serial, check=False)
        if res.stdout.decode("utf-8", errors="ignore").strip() == "1":
            return
        time.sleep(1.5)
    raise TimeoutError("Emulator did not finish booting in time")


def screencap(out_path: Path, serial: str | None = None) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    res = run_adb(["exec-out", "screencap", "-p"], serial=serial)
    out_path.write_bytes(res.stdout)
    print(f"Saved screenshot: {out_path}")


def dump_ui(serial: str | None = None) -> list[dict[str, str]]:
    run_adb(["shell", "uiautomator", "dump", "/sdcard/ui_dump.xml"], serial=serial)
    res = run_adb(["exec-out", "cat", "/sdcard/ui_dump.xml"], serial=serial)
    xml_text = res.stdout.decode("utf-8", errors="replace")
    root = ET.fromstring(xml_text)
    nodes: list[dict[str, str]] = []
    for elem in root.iter("node"):
        text = elem.attrib.get("text", "")
        desc = elem.attrib.get("content-desc", "")
        bounds = elem.attrib.get("bounds", "")
        cls = elem.attrib.get("class", "")
        clickable = elem.attrib.get("clickable", "")
        if text or desc or clickable == "true":
            nodes.append({
                "text": text,
                "desc": desc,
                "bounds": bounds,
                "class": cls,
                "clickable": clickable,
            })
    return nodes


def main() -> int:
    parser = argparse.ArgumentParser(description="ADB screenshot & UI helper")
    parser.add_argument("--serial", default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("wait-boot")
    p_cap = sub.add_parser("cap")
    p_cap.add_argument("out", type=Path)

    sub.add_parser("dump")

    p_tap = sub.add_parser("tap")
    p_tap.add_argument("x", type=int)
    p_tap.add_argument("y", type=int)

    p_lp = sub.add_parser("longpress")
    p_lp.add_argument("x", type=int)
    p_lp.add_argument("y", type=int)
    p_lp.add_argument("--ms", type=int, default=900)

    p_sw = sub.add_parser("swipe")
    p_sw.add_argument("x1", type=int)
    p_sw.add_argument("y1", type=int)
    p_sw.add_argument("x2", type=int)
    p_sw.add_argument("y2", type=int)
    p_sw.add_argument("--ms", type=int, default=300)

    args = parser.parse_args()
    if args.cmd == "wait-boot":
        wait_for_boot(args.serial)
        print("Boot completed")
    elif args.cmd == "cap":
        screencap(args.out, args.serial)
    elif args.cmd == "dump":
        for n in dump_ui(args.serial):
            print(n)
    elif args.cmd == "tap":
        run_adb(["shell", "input", "tap", str(args.x), str(args.y)], serial=args.serial)
    elif args.cmd == "longpress":
        run_adb(
            ["shell", "input", "swipe", str(args.x), str(args.y), str(args.x), str(args.y), str(args.ms)],
            serial=args.serial,
        )
    elif args.cmd == "swipe":
        run_adb(
            ["shell", "input", "swipe", str(args.x1), str(args.y1), str(args.x2), str(args.y2), str(args.ms)],
            serial=args.serial,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
