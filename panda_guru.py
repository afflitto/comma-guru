import argparse
import os
import re
from panda import Panda, PandaDFU


def version(args):
    panda = Panda(args.serial)
    version = panda.get_version()
    signature = panda.get_signature()
    serial = ":".join(panda.get_serial())
    mcu_type = panda.get_mcu_type()
    print("Hardware info:")
    print(f"\tserial_number={serial}")
    print(f"\tmcu_type={mcu_type.name}")
    print("Firmware info:")
    print(f"\tversion={version}")
    print("\tsignature:")
    print(signature.hex())


def flash(args):
    if args.bin is None:
        raise ValueError("--bin is required")
    if not os.path.isfile(args.bin):
        raise ValueError(f"{args.bin} is not a file")
    
    panda = Panda(args.serial)
    print(f"Current firmware version: {panda.get_version()}")

    if not args.force and not panda.up_to_date(args.bin):
        print("Firmware is already up to date, use --force to flash anyway")

    print("Resetting to bootstub...")
    if not panda.bootstub:
        panda.reset(enter_bootstub=True)
    assert panda.bootstub
    print(f"Bootstub version: {panda.get_version()}")
    
    with open(args.bin, "rb") as f:
        bin = f.read()
    
    print("Flashing panda firmware...")
    Panda.flash_static(panda._handle, bin, mcu_type=panda._mcu_type)
    panda.reconnect()
    print(f"New firmware version: {panda.get_version()}")


def recover(args):
    if args.bin is None:
        raise ValueError("--bin is required")
    if not os.path.isfile(args.bin):
        raise ValueError(f"{args.bin} is not a file")
    
    panda = Panda(args.serial)
    dfu_serial = panda.get_dfu_serial()
    if dfu_serial is None:
        raise ValueError("Could not get DFU serial")
    
    print("Resetting Panda to bootloader")
    panda.reset(enter_bootstub=True)
    panda.reset(enter_bootloader=True)

    print("Waiting for DFU...")
    if not panda.wait_for_dfu(dfu_serial=dfu_serial, timeout=args.timeout):
        raise ValueError("Timeout waiting for DFU")
    
    print("Connected to DFU, flashing bootstub...")
    dfu = PandaDFU(dfu_serial=dfu_serial)
    with open(args.bin, "rb") as f:
        bin = f.read()
    dfu.program_bootstub(bin)
    print("Resetting panda...")
    dfu.reset()
    print("DFU recovery successful")
    print("Run the flash command to flash panda firmware")


def reset(args):
    print("Resetting panda...")
    panda = Panda(args.serial)
    panda.reset()


def bin_info(args):
    if args.bin is None:
        raise ValueError("--bin is required")
    
    version_regex = re.compile(rb"([v0-9.])*-?(DEV)?-([0-9a-f]){8}-(DEBUG)?(RELEASE)?")
    with open(args.bin, "rb") as f:
        bin = f.read()

    matches = version_regex.finditer(bin)
    print("Possible version matches:")
    for match in matches:
        try:
            print(match.group(0).decode("utf-8"))
        except:
            print(match.group(0))

    print("Signature:")
    print(Panda.get_signature_from_firmware(args.bin).hex())


def help(args):
    print("version: print info about the current panda device")
    print("flash --bin <path-to-bin>: flash path-to-bin to the device")
    print("recover --bin <path-to-bootstub> [--timeout timeout]: flash path-to-bootstub via dfu mode, dfu timeout defaults to 60")
    print("bin-info --bin <path-to-bin>: print version info of path-to-bin")
    print("reset: reset panda")


COMMANDS = {
    "version": version,
    "flash": flash,
    "recover": recover,
    "bin-info": bin_info,
    "reset": reset,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser("panda.py")
    parser.add_argument("command", choices=COMMANDS.keys())
    parser.add_argument("--serial", type=str, help="Serial connection to use", default=None)
    parser.add_argument("--bin", type=str, help="Path to panda.bin", default=None)
    parser.add_argument("--force", action="store_true", help="Force flash even if panda is already up to date")
    parser.add_argument("--timeout", type=int, help="Seconds to wait for DFU", default=60)
    args = parser.parse_args()

    command = COMMANDS[args.command]
    command(args)