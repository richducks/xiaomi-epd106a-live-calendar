#!/usr/bin/env python3
"""Create a local OTA package from *user supplied* recovery tools and image.

Does NOT flash a device, redistribute stock firmware, or circumvent Recovery
signature verification. Supports only Xiaomi EPD106A / virgo-perf1.
"""
from __future__ import annotations
import argparse
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

DEVICE = "virgo-perf1"
RESCUE_NAME = "/cache/eink-calendar-rescue.disable"
RESCUE_MARKER = "DISABLE_EINK_CALENDAR_V1\n"
MODEL_CHECK = 'assert(getprop("ro.product.device") == "virgo-perf1");'

def verify_boot_image(path: Path) -> str:
    length = path.stat().st_size
    if length != 32 * 1024 * 1024:
        raise ValueError(f"Expected 32MiB EPD106A boot partition image; got {length} bytes")
    with path.open("rb") as src:
        magic = src.read(8)
        header = src.read(40)
        if magic != b"ANDROID!":
            raise ValueError("Not an Android boot image (ANDROID! magic missing)")
        # Classic boot image: kernel_size at offset 8, ramdisk_size at offset 16
        kernel, ramdisk = struct.unpack_from("<II", header, 0)[0], struct.unpack_from("<I", header, 8)[0]
        page = struct.unpack_from("<I", header, 28)[0]
        if not (1024 <= kernel < length and 1024 <= ramdisk < length and page in (2048, 4096)):
            raise ValueError("Malformed boot image dimensions/page size")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest

def build_zip(mode: str, update_binary: Path, output: Path,
              boot: Path | None = None) -> str | None:
    if not update_binary.is_file():
        raise FileNotFoundError(f"User-supplied recovery update-binary missing: {update_binary}")
    boot_hash = None
    if mode == "rescue":
        script = "\n".join([
            'ui_print("EPD106A: emergency disable live calendar module");',
            MODEL_CHECK,
            f'assert(package_extract_file("rescue.flag", "{RESCUE_NAME}"));',
            'ui_print("RECOVERY_RESCUE_MARKER_INSTALLED");',
            'ui_print("No boot/system/vendor images flashed");',
            "",
        ])
    else:
        if boot is None or not boot.is_file():
            raise FileNotFoundError("Root flash mode requires your own Magisk-patched boot.img")
        boot_hash = verify_boot_image(boot)
        script = "\n".join([
            'ui_print("EPD106A: write USER-PROVIDED Magisk-patched boot image");',
            MODEL_CHECK,
            f'ui_print("Boot SHA-256: {boot_hash}");',
            'assert(package_extract_file("boot.img", "/dev/block/by-name/boot"));',
            'ui_print("Boot image written. Reboot cautiously.");',
            "",
        ])
    if output.exists():
        raise FileExistsError(f"Won't overwrite existing file: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=6) as dst:
        dst.write(update_binary, "META-INF/com/google/android/update-binary")
        dst.writestr("META-INF/com/google/android/updater-script", script)
        if mode == "rescue":
            dst.writestr("rescue.flag", RESCUE_MARKER)
        else:
            dst.write(boot, "boot.img")
    return boot_hash

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True, choices=("rescue", "root-flash"))
    ap.add_argument("--update-binary", type=Path, required=True,
                    help="update-binary legally extracted by YOU for your firmware")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--boot-image", type=Path)
    ap.add_argument("--accept-root-flash-risk", action="store_true")
    ap.add_argument("--signapk", type=Path, help="AOSP signapk.jar (required for whole-file OTA signing)")
    ap.add_argument("--cert", type=Path, help="certificate trusted by your Recovery")
    ap.add_argument("--private-key", type=Path, help="your local signing key, never upload it")
    args = ap.parse_args(argv)
    if args.mode == "root-flash":
        if not args.accept_root_flash_risk:
            ap.error("root-flash requires --accept-root-flash-risk")
        if not args.boot_image:
            ap.error("root-flash requires --boot-image")
    else:
        if args.boot_image:
            ap.error("rescue mode cannot carry boot image")
    if args.output.suffix.lower() != ".zip":
        ap.error("--output must end with .zip")
    signing = (args.signapk, args.cert, args.private_key)
    if any(signing) and not all(signing):
        ap.error("--signapk, --cert and --private-key must be supplied together")
    if not all(signing):
        ap.error("Recovery requires a whole-file signature; provide --signapk --cert --private-key")
    with tempfile.TemporaryDirectory(prefix="epd106a-ota-") as work:
        unsigned = Path(work) / "unsigned.zip"
        boot_hash = build_zip(args.mode, args.update_binary, unsigned, args.boot_image)
        if args.output.exists():
            raise FileExistsError(f"Won't overwrite existing file: {args.output}")
        subprocess.run(["java", "-jar", str(args.signapk), "-w", str(args.cert),
                        str(args.private_key), str(unsigned), str(args.output)], check=True)
        with args.output.open("rb") as f:
            f.seek(-6, os.SEEK_END)
            footer = f.read(6)
        if footer[2:4] != bytes((255,255)):
            args.output.unlink(missing_ok=True)
            raise ValueError("Signing output is not a valid whole-file OTA signature")
    if boot_hash:
        print(f"User-supplied boot SHA-256: {boot_hash}")
    print(f"CREATED {args.output} SHA-256 {hashlib.sha256(args.output.read_bytes()).hexdigest()}")
    print("No device flashed. Keep the signed ZIP and your own keys private if it contains a device-specific boot image.")

if __name__ == "__main__":
    main()
