#!/usr/bin/env python3
"""Report the identity and feature markers of a built kernel image.

Usage: verify_kernel.py <dir-with-boot-images>
Exits non-zero only if no image is found at all - the rest is reporting, so a
build still uploads its artifacts even when a marker looks wrong.
"""
import gzip, io, os, re, sys

def main(d):
    for name in ('Image.gz-dtb', 'Image.gz', 'Image'):
        p = os.path.join(d, name)
        if os.path.exists(p):
            break
    else:
        print(f'ERROR: no kernel image in {d}', file=sys.stderr)
        return 1

    raw = open(p, 'rb').read()
    print(f'image : {p}  ({len(raw)} bytes)')
    if raw[:3] == b'\x1f\x8b\x08':
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        print(f'        gunzipped -> {len(raw)} bytes')

    m = re.search(rb'Linux version [\x20-\x7e]{0,160}', raw)
    banner = m.group(0).decode() if m else None
    print(f'banner: {banner or "(not found)"}')

    for s in (b'susfs', b'SUSFS', b'KernelSU', b'ReSukiSU'):
        print(f'  contains {s.decode():10s}: {s in raw}')

    if banner:
        # the version token is everything before the " (user@host)" part
        ver = banner.split('(')[0]
        if '+' in ver:
            print('WARN: banner carries a trailing "+" (dirty-tree marker); '
                  'stock Samsung has none - is .scmversion missing?')
        for marker in ('\U0001f1fa', 'dirty'):
            if marker in banner:
                print(f'WARN: banner contains custom marker {marker!r}')
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else '.'))
