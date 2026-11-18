#!/usr/bin/env python3
"""Active USB test of the Pi's CarLife authentication response.

Targets only serial cp2cl-pi5. Uses only the pinned public key, never the private
key, and verifies the returned RSA block before reporting authentication success.
This synthetic host does not establish real NTG6 compatibility.
"""
import base64
import argparse
import ctypes as c
import ctypes.util
import importlib.util
from pathlib import Path
import struct
import time

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("carlife_key", ROOT / "scripts/carlife-key.py")
keys = importlib.util.module_from_spec(spec)
spec.loader.exec_module(keys)

u = c.CDLL(ctypes.util.find_library("usb-1.0"))
for name, arguments, result in [
    ("init", [c.POINTER(c.c_void_p)], c.c_int),
    ("open_device_with_vid_pid", [c.c_void_p, c.c_uint16, c.c_uint16], c.c_void_p),
    ("get_string_descriptor_ascii", [c.c_void_p, c.c_uint8, c.c_void_p, c.c_int], c.c_int),
    ("control_transfer", [c.c_void_p, c.c_uint8, c.c_uint8, c.c_uint16, c.c_uint16,
                          c.c_void_p, c.c_uint16, c.c_uint], c.c_int),
    ("bulk_transfer", [c.c_void_p, c.c_ubyte, c.c_void_p, c.c_int,
                       c.POINTER(c.c_int), c.c_uint], c.c_int),
    ("claim_interface", [c.c_void_p, c.c_int], c.c_int),
    ("release_interface", [c.c_void_p, c.c_int], c.c_int),
    ("close", [c.c_void_p], None),
    ("exit", [c.c_void_p], None),
]:
    function = getattr(u, "libusb_" + name)
    function.argtypes, function.restype = arguments, result


def control(handle, kind, request, value=0, index=0, data=b"", length=None):
    length = len(data) if length is None else length
    buffer = c.create_string_buffer(max(1, length))
    if data:
        c.memmove(buffer, data, len(data))
    count = u.libusb_control_transfer(handle, kind, request, value, index,
                                    buffer, length, 3000)
    if count != length:
        raise RuntimeError(f"Control request {request}: expected {length}, got {count}")
    return buffer.raw[:count]


def target(context, pid):
    handle = u.libusb_open_device_with_vid_pid(context, 0x18d1, pid)
    if not handle:
        return None
    try:
        descriptor = control(handle, 0x80, 6, 0x100, length=18)
        serial = c.create_string_buffer(256)
        count = u.libusb_get_string_descriptor_ascii(handle, descriptor[16], serial, 255)
        if count <= 0 or serial.value != b"cp2cl-pi5":
            raise RuntimeError("Refusing USB device with unexpected serial")
    except BaseException:
        u.libusb_close(handle)
        raise
    return handle


def transfer(handle, endpoint, data=None):
    length = len(data) if data is not None else 65536
    buffer = c.create_string_buffer(length)
    if data is not None:
        c.memmove(buffer, data, length)
    done = c.c_int()
    result = u.libusb_bulk_transfer(handle, endpoint, buffer, length, c.byref(done), 4000)
    if result or (data is not None and done.value != length):
        raise RuntimeError(f"Bulk transfer: result={result}, bytes={done.value}")
    if done.value == 0:
        raise RuntimeError("Empty bulk transfer")
    return buffer.raw[:done.value]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accessory", action="store_true",
                        help="require an already-accessory Pi; do not send AOA requests")
    parser.add_argument("--idle-seconds", type=int, default=0, choices=range(61),
                        metavar="0..60", help="wait before starting the CarLife protocol")
    parser.add_argument("--pause-resume", action="store_true",
                        help="emulate DAIMLER desktop transitions and verify background keepalive")
    args = parser.parse_args()
    context = c.c_void_p()
    if u.libusb_init(c.byref(context)):
        raise RuntimeError("libusb initialization failed")
    handle, claimed = None, None
    try:
        if args.accessory:
            handle = target(context, 0x2d00)
            print("Direct accessory test: no AOA 51/52/53 requests sent")
        else:
            handle = target(context, 0x4ee1)
            if not handle:
                raise RuntimeError("Initial Pi gadget not found (or insufficient USB permissions)")
            assert control(handle, 0xc0, 51, length=2) == b"\x02\x00"
            for index, text in enumerate([b"Baidu", b"CarLife", b"Baidu CarLife",
                                          b"1.0.0", b"http://carlife.baidu.com/", b"auth-smoke"]):
                control(handle, 0x40, 52, index=index, data=text + b"\0")
            control(handle, 0x40, 53)
            u.libusb_close(handle)
            handle = None
            for _ in range(80):
                time.sleep(0.1)
                handle = target(context, 0x2d00)
                if handle:
                    break
        if not handle:
            raise RuntimeError("Accessory gadget not found (or insufficient USB permissions)")
        header = control(handle, 0x80, 6, 0x200, length=9)
        config = control(handle, 0x80, 6, 0x200,
                         length=struct.unpack_from("<H", header, 2)[0])
        offset, interface, endpoints = 0, None, []
        while offset < len(config):
            size, kind = config[offset:offset+2]
            if size < 2 or offset + size > len(config):
                raise RuntimeError("Invalid USB descriptor")
            item = config[offset:offset+size]
            if kind == 4:
                interface = item[2] if item[5] == 0xff else None
            if kind == 5 and interface is not None:
                endpoints.append(item[2])
            offset += size
        assert interface is not None and len(endpoints) == 2
        endpoint_in = next(ep for ep in endpoints if ep & 0x80)
        endpoint_out = next(ep for ep in endpoints if not ep & 0x80)
        assert u.libusb_claim_interface(handle, interface) == 0
        claimed = interface
        incoming = bytearray()
        if args.idle_seconds:
            print(f"Waiting {args.idle_seconds}s before the first CarLife message", flush=True)
            time.sleep(args.idle_seconds)

        def send(message, body):
            transfer(handle, endpoint_out, struct.pack(">II", 1, len(body)+8))
            transfer(handle, endpoint_out, struct.pack(">HHI", len(body), 0, message)+body)

        def expect(wanted, forbid_video=False):
            def read_more():
                try:
                    incoming.extend(transfer(handle, endpoint_in))
                except RuntimeError as error:
                    raise RuntimeError(f"Response {wanted:#x} stalled: buffered="
                                       f"{len(incoming)} prefix={incoming[:32].hex()}") from error

            for _ in range(40):
                while len(incoming) < 8:
                    read_more()
                channel, size = struct.unpack_from(">II", incoming)
                assert 8 <= size <= 640*1024
                while len(incoming) < size+8:
                    read_more()
                frame = bytes(incoming[8:size+8])
                del incoming[:size+8]
                head = 8 if channel in (1, 6) else 12
                message = struct.unpack_from(">I", frame, head-4)[0]
                if forbid_video and message == 0x20001:
                    raise RuntimeError("Video data sent while NTG6 requested PAUSE")
                if channel == wanted >> 16 and message == wanted:
                    return frame[head:]
            raise RuntimeError(f"Response {wanted:#x} not received")

        send(0x18001, b"\x08\x02\x10\x00")
        expect(0x10002)
        for challenge in (b"384_1.0.0", b"1234567890_1.0.0"):
            send(0x18048, b"\x0a"+bytes([len(challenge)])+challenge)
            answer = expect(0x10049)
            assert answer[0] == 0x0a
            length, shift, index = 0, 0, 1
            while True:
                byte = answer[index]
                index += 1
                length |= (byte & 127) << shift
                if byte < 128:
                    break
                shift += 7
                assert shift <= 28
            assert index+length == len(answer)
            signature = base64.b64decode(answer[index:], validate=True)
            public = keys.expected_public().public_numbers()
            assert len(signature) == 128
            # Verify Java RSA/ECB/PKCS1Padding private-key operation: the public
            # operation recovers exactly the original challenge with type-1 padding.
            block = pow(int.from_bytes(signature, "big"), public.e, public.n).to_bytes(128, "big")
            expected = b"\x00\x01"+b"\xff"*(128-len(challenge)-3)+b"\x00"+challenge
            assert block == expected, "CarLife authentication signature rejected"
            print(f"PASS: challenge {challenge.decode()} returned a verified RSA response")
        send(0x1804a, b"\x08\x01")
        time.sleep(0.3)
        print("PASS: accessory USB + CarLife 2.0 + two authentication challenges over real Pi USB")
        if args.pause_resume:
            send(0x18027, b"\x22\x08"+b"20062105")
            send(0x18007, bytes.fromhex("08800f10d005181e"))
            assert expect(0x10008) == bytes.fromhex("08800f10d005183c")
            send(0x18003, b"")
            expect(0x10004)
            expect(0x1004b)
            send(0x18009, b"")
            expect(0x1001b)
            expect(0x20001)
            for cycle in range(1, 4):
                send(0x1800a, b"")
                # Frames already queued before PAUSE can precede its first
                # heartbeat. After that, keepalive must contain no video data.
                expect(0x20002)
                deadline, count = time.monotonic()+6, 0
                while time.monotonic() < deadline:
                    expect(0x20002, forbid_video=True)
                    count += 1
                assert count >= 20, f"Background heartbeat too slow: {count} in 6 seconds"
                send(0x18025, b"")
                expect(0x1004c, forbid_video=True)
                send(0x18009, b"")
                expect(0x1001b)
                expect(0x20001)
                print(f"PASS: desktop/resume cycle={cycle}; paused 6s with {count} heartbeats; video restored",
                      flush=True)
        print("Synthetic host only; real NTG6 acceptance remains untested")
    finally:
        if handle:
            if claimed is not None:
                u.libusb_release_interface(handle, claimed)
            u.libusb_close(handle)
        u.libusb_exit(context)


if __name__ == "__main__":
    main()
