"""Minimal PMX / PMD reader that extracts bone data for skeleton analysis.

For every model found under <dir> it records, per bone: name, English name,
position, parent index, flags (PMX bone flags / PMD bone type) and the total
vertex weight assigned to the bone.

Usage: python tools/pmx_bones.py <dir> [--json out.json]
"""
import json
import os
import struct
import sys


class Reader:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def read(self, n):
        b = self.d[self.p:self.p + n]
        self.p += n
        return b

    def skip(self, n):
        self.p += n

    def u8(self):
        return self.read(1)[0]

    def i32(self):
        return struct.unpack('<i', self.read(4))[0]

    def u16(self):
        return struct.unpack('<H', self.read(2))[0]

    def f32(self):
        return struct.unpack('<f', self.read(4))[0]

    def vec3(self):
        return struct.unpack('<3f', self.read(12))

    def idx(self, size):
        if size == 1:
            return struct.unpack('<b', self.read(1))[0]
        if size == 2:
            return struct.unpack('<h', self.read(2))[0]
        return struct.unpack('<i', self.read(4))[0]


def read_pmx(data):
    r = Reader(data)
    assert r.read(4) == b'PMX '
    r.f32()
    n = r.u8()
    g = list(r.read(n))
    enc = 'utf-16-le' if g[0] == 0 else 'utf-8'
    add_uv, vsz, tsz, msz, bsz = g[1], g[2], g[3], g[4], g[5]

    def text():
        ln = r.i32()
        return r.read(ln).decode(enc, errors='replace')

    model_name = text(); text(); text(); text()
    # vertices
    wsum = {}

    def addw(i, w):
        if i >= 0 and w > 0:
            wsum[i] = wsum.get(i, 0.0) + w

    for _ in range(r.i32()):
        r.skip(32 + 16 * add_uv)
        wt = r.u8()
        if wt == 0:
            addw(r.idx(bsz), 1.0)
        elif wt in (1, 3):
            a = r.idx(bsz); b = r.idx(bsz); w = r.f32()
            addw(a, w); addw(b, 1.0 - w)
            if wt == 3:
                r.skip(36)
        elif wt in (2, 4):
            ids = [r.idx(bsz) for _ in range(4)]
            ws = struct.unpack('<4f', r.read(16))
            for i, w in zip(ids, ws):
                addw(i, w)
        else:
            raise ValueError('bad weight type %d' % wt)
        r.skip(4)
    r.skip(r.i32() * vsz)
    for _ in range(r.i32()):
        text()
    for _ in range(r.i32()):
        text(); text()
        r.skip(16 + 12 + 4 + 12 + 1 + 16 + 4)
        r.skip(tsz * 2)
        r.skip(1)
        toon = r.u8()
        r.skip(tsz if toon == 0 else 1)
        text()
        r.skip(4)
    bones = []
    for _ in range(r.i32()):
        name = text(); name_e = text()
        pos = r.vec3()
        parent = r.idx(bsz)
        r.i32()
        flags = r.u16()
        if flags & 0x1:
            r.idx(bsz)
        else:
            r.vec3()
        if flags & 0x300:
            r.idx(bsz); r.f32()
        if flags & 0x400:
            r.vec3()
        if flags & 0x800:
            r.vec3(); r.vec3()
        if flags & 0x2000:
            r.i32()
        if flags & 0x20:
            r.idx(bsz); r.i32(); r.f32()
            for _ in range(r.i32()):
                r.idx(bsz)
                if r.u8():
                    r.vec3(); r.vec3()
        bones.append({'name': name, 'name_e': name_e, 'pos': pos, 'parent': parent,
                      'flags': flags, 'weight': round(wsum.get(len(bones), 0.0), 2)})
    return model_name, bones


def read_pmd(data):
    r = Reader(data)
    assert r.read(3) == b'Pmd'
    r.f32()
    model_name = r.read(20).split(b'\0')[0].decode('cp932', errors='replace')
    r.skip(256)
    wsum = {}
    for _ in range(struct.unpack('<I', r.read(4))[0]):
        r.skip(32)
        a, b = struct.unpack('<HH', r.read(4))
        w = r.u8() / 100.0
        r.skip(1)
        wsum[a] = wsum.get(a, 0.0) + w
        wsum[b] = wsum.get(b, 0.0) + (1.0 - w)
    r.skip(struct.unpack('<I', r.read(4))[0] * 2)
    r.skip(struct.unpack('<I', r.read(4))[0] * 70)
    bones = []
    for _ in range(r.u16()):
        name = r.read(20).split(b'\0')[0].decode('cp932', errors='replace')
        parent = r.u16()
        r.u16()
        btype = r.u8()
        r.u16()
        pos = r.vec3()
        bones.append({'name': name, 'name_e': '', 'pos': pos,
                      'parent': -1 if parent == 0xFFFF else parent, 'flags': btype,
                      'weight': round(wsum.get(len(bones), 0.0), 2)})
    return model_name, bones


def read_model(path):
    with open(path, 'rb') as f:
        data = f.read()
    if data[:4] == b'PMX ':
        return read_pmx(data)
    if data[:3] == b'Pmd':
        return read_pmd(data)
    raise ValueError('unknown format')


def main():
    root = sys.argv[1]
    out = {}
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.lower().endswith(('.pmx', '.pmd')):
                p = os.path.join(dp, f)
                try:
                    name, bones = read_model(p)
                    out[os.path.relpath(p, root)] = {'model': name, 'bones': bones}
                except Exception as e:
                    print('ERR', p, e, file=sys.stderr)
    if '--json' in sys.argv:
        with open(sys.argv[sys.argv.index('--json') + 1], 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False)
    print(len(out), 'models parsed')


if __name__ == '__main__':
    main()
