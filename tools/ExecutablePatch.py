#!/usr/bin/env python3
import argparse
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

FRIDA = "Frida.framework"
ORPHAN = 0xFD
UA = {"User-Agent": "curl/8"}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60)


def resolve(url):
    if not url.endswith(".ipa"):
        page = get(url).read().decode("utf-8", "ignore")
        for m in re.findall(r'https?://[^"\'<>\s]+', page):
            if "latest_bs_i" in m or m.endswith(".ipa"):
                url = m
                break
    return get(url).geturl()


def app_of(z):
    ins = [n for n in z.namelist() if n.startswith("Payload/") and n.endswith(".app/Info.plist") and n.count("/") == 2]
    if len(ins) != 1:
        sys.exit("app entries: %r" % ins)
    app = ins[0][: -len("Info.plist") - 1]
    return app, plistlib.loads(z.read(ins[0]))["CFBundleExecutable"]


def table(raw, b):
    cf = b.dyld_chained_fixups
    step = 8 if int(cf.imports_format) == 3 else 4
    return cf.data_offset + cf.imports_offset, step, cf.imports_count


def ords(raw, b):
    off, step, cnt = table(raw, b)
    mask = 0xFFFF if step == 8 else 0xFF
    return [int.from_bytes(raw[off + i * step: off + (i + 1) * step], "little") & mask for i in range(cnt)]


def shift(raw, b, drop):
    off, step, cnt = table(raw, b)
    mask = 0xFFFF if step == 8 else 0xFF
    buf = bytearray(raw)
    hit = 0
    for i in range(cnt):
        p = off + i * step
        w = int.from_bytes(buf[p:p + step], "little")
        lo = w & mask
        if lo == drop:
            w = (w & ~mask) | ORPHAN
        elif 0 < lo < 0x80 and lo > drop:
            w -= 1
        else:
            continue
        buf[p:p + step] = w.to_bytes(step, "little")
        hit += 1
    return bytes(buf), hit


def check(path, libs, cnt):
    import lief

    b = lief.MachO.parse(path).at(0)
    o = ords(open(path, "rb").read(), b)
    live = [x for x in o if x < 0x80]
    assert len(b.libraries) == libs, "libs %d" % len(b.libraries)
    assert len(o) == cnt, "imports %d" % len(o)
    assert not any(FRIDA in c.name for c in b.libraries), "load command left"
    assert b.has_dyld_chained_fixups, "fixups lost"
    assert not b.has_code_signature, "signature left"
    assert max(live) <= libs, "ordinal %d > libs %d" % (max(live), libs)
    return max(live)


def drop_lc(data, work):
    import lief

    src = os.path.join(work, "exec")
    open(src, "wb").write(data)
    b = lief.MachO.parse(src).at(0)
    cnt = b.dyld_chained_fixups.imports_count
    libs = len(b.libraries)
    pos = [i for i, c in enumerate(b.libraries) if FRIDA in c.name]
    if not pos:
        print("lc: already absent")
        return data
    if not b.has_dyld_chained_fixups:
        sys.exit("no chained fixups")
    raw, hit = shift(data, b, pos[0] + 1)
    open(src, "wb").write(raw)
    b2 = lief.MachO.parse(src).at(0)
    b2.remove([c for c in b2.libraries if FRIDA in c.name][0])
    b2.remove_signature()
    b2.write(src)
    mx = check(src, libs - 1, cnt)
    print("lc: dropped ordinal %d, libs %d -> %d, imports %d, max ordinal %d" % (pos[0] + 1, libs, libs - 1, hit, mx))
    return open(src, "rb").read()


def run(cmd, cwd=None, ok=(0,)):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if p.returncode not in ok:
        sys.exit("%s: %s" % (" ".join(cmd), p.stderr.strip() or p.stdout.strip()))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve")
    ap.add_argument("--ipa")
    ap.add_argument("--exe-dir", default=".")
    ap.add_argument("--out")
    ap.add_argument("--drop-lc", action="store_true")
    a = ap.parse_args()
    if a.resolve:
        print(resolve(a.resolve))
        return
    if not a.ipa:
        sys.exit("need --ipa")

    z = zipfile.ZipFile(a.ipa)
    app, ex = app_of(z)
    entry = "%s/%s" % (app, ex)
    data = z.read(entry)
    z.close()
    print("app: %s, exec: %s (%d bytes)" % (app, ex, len(data)))

    work = tempfile.mkdtemp()
    out = drop_lc(data, work) if a.drop_lc else data

    os.makedirs(a.exe_dir, exist_ok=True)
    dst = os.path.join(a.exe_dir, os.path.basename(ex))
    open(dst, "wb").write(out)
    print("exec: %s (%d bytes)" % (dst, len(out)))

    if not a.out:
        return
    shutil.copyfile(a.ipa, a.out)
    run(["zip", "-q", "-d", os.path.abspath(a.out), "%s/Frameworks/%s/*" % (app, FRIDA)], ok=(0, 12))
    if a.drop_lc:
        w = os.path.join(work, entry)
        os.makedirs(os.path.dirname(w), exist_ok=True)
        open(w, "wb").write(out)
        run(["zip", "-q", "-X", os.path.abspath(a.out), entry], cwd=work)
    z = zipfile.ZipFile(a.out)
    left = [n for n in z.namelist() if FRIDA in n]
    size = z.getinfo(entry).file_size
    z.close()
    assert not left, "left: %r" % left
    assert size == len(out), "exec size %d" % size
    print("ipa: %s, frida entries %d" % (a.out, len(left)))


if __name__ == "__main__":
    main()
