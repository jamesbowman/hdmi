from PIL import Image
import numpy as np
import sys
import struct

B0 = b'\x00'

def ecc(v, n):
    lfsr = 0
    for i in range(n):
        f = (v ^ lfsr) & 1
        lfsr >>= 1
        v >>= 1
        if f:
            lfsr ^= 0b10000011
    return lfsr

def parity(x):
    p = 0
    while x:
        p ^= (x & 1)
        x >>= 1
    return p

terc4_codes = [
0b1010011100,
0b1001100011,
0b1011100100,
0b1011100010,
0b0101110001,
0b0100011110,
0b0110001110,
0b0100111100,
0b1011001100,
0b0100111001,
0b0110011100,
0b1011000110,
0b1010001110,
0b1001110001,
0b0101100011,
0b1011000011
]

control_codes = [
0b1101010100,
0b0010101011,
0b0101010100,
0b1010101011
]

video_guards = [
0b1011001100,
0b0100110011,
0b1011001100
]

data_guards = [
None,
0b0100110011,
0b0100110011
]

data_guards_0 = [
0b1010001110,
0b1001110001,
0b0101100011,
0b1011000011
]

def tmds(x):
    # Decode 10-bit to 8. Section 5.4.4.2
    if x & 0x200:
        x ^= 0xff
    q = 0xff & ((x << 1) ^ x)
    if (x & 0x100) == 0:
        q ^= 0xfe
    return q
tmds_table = [tmds(i) for i in range(1024)]

def bin10(x, n = 10):
    return bin(x)[2:].rjust(n, '0')

class Decoder:
    def __init__(self):
        self.window = ''
        self.in_data_island = False
        self.in_video_data = False
        self.bch2 = 0
        self.bch3 = 0
        self.bch = [0,0,0,0]
        self.count = 0
        self.regen_clock = set()

        self.rgb = []

        self.afc = 0        # aligned frame counter
        self.channel_status = [0, 0]

    def audio_frame(self, bb):
        (l24,) = struct.unpack("<I", bb[:3] + B0)
        (r24,) = struct.unpack("<I", bb[3:6] + B0)
        for (lr, sample) in enumerate((l24, r24)):
            pcuv = 0xf & (bb[6] >> (4 * lr))
            p = parity(pcuv) ^ parity(sample)
            assert p == 0
            assert (pcuv & 3) == 0, "User and Valid bits should be zero"
            c = 1 & (pcuv >> 2)
            self.channel_status[lr] |= (c << self.afc)
        self.afc += 1
        if self.afc == 192:
            # 60958-3 page 5
            print("%048x %048x" % tuple(self.channel_status))

    def handle_island(self):
        # Section 5.3.1
        hb0 = self.bch2 & 0xff
        hb1 = (self.bch2 >> 8) & 0xff
        hb2 = (self.bch2 >> 16) & 0xff

        assert all([ecc(x, 56) == (x >> 56) for x in self.bch])

        sb = [struct.pack("Q", b)[:7] for b in self.bch]

        if hb0 == 0x00:
            return
        elif hb0 == 0x01:
            assert len(set(self.bch)) == 1
            # print("SB0-6:", ",".join(['%02x'%b for b in sb]))
            (CTS,) = struct.unpack(">I", sb[0][0:4])
            (N,)   = struct.unpack(">I", b'\x00' + sb[0][4:])
            # print('N', N, 'CTS', CTS, 74.25e6 * N / CTS)
            self.regen_clock.add((74.25e6 * N / CTS) / 128)
        elif hb0 == 0x02:
            for d in range(4):
                if hb1 & (1 << d):
                    if (hb2 >> 4) & (1 << d):
                        self.afc = 0
                        self.channel_status = [0, 0]
                    self.audio_frame(sb[d])
        else:
            print("Unhandled packet code %02x" % hb0)

    def datum(self, ch):
        assert len(ch) == 3
        assert all([0 <= x < 1024 for x in ch])
        # sys.stdout.write(str(cn) + " " + bin(x)[2:].rjust(10, '0') + " ")
        sx = set(ch)

        (hsync, vsync) = (0, 0)
        d = 'xxx' # 'xxx %s' % bin10(ch[0])
        rgb = (0, 0, 0)

        if ch == video_guards:
            d = 'VIDEO GUARD'
            self.window += 'v'
            (hsync, vsync) = (0, 0)
            rgb = (0, 128, 0)
        elif ch[0] in data_guards_0 and ch[1:] == data_guards[1:]:
            d = 'DATA GUARD'
            vh = data_guards_0.index(ch[0])
            hsync = vh & 1
            vsync = (vh >> 1) & 1
            self.window += 'd'
            rgb = (0, 0, 128)
        elif sx <= set(control_codes):
            # Section 5.1.2: [ CTL3 CTL2 CTL1 CTL0 VSYNC HSYNC ]
            ctl6 = sum([(control_codes.index(x) << (2 * i)) for (i, x) in enumerate(ch)])
            hsync = ctl6 & 1
            vsync = (ctl6 >> 1) & 1
            ctl = ctl6 >> 2

            d = 'CONTROL ' + bin10(ctl, 4)
            if ctl == 0b0001:
                d = 'VIDEO preamble'
                self.window += 'V'
                rgb = (64, 64, 0)
            if ctl == 0b0101:
                d = 'DATA preamble'
                self.window += 'D'
                rgb = (0, 64, 64)
            self.in_video_data = False
        elif self.in_data_island:
            terc = [terc4_codes.index(x) for x in ch]
            d = 'TERC %s %s %s' % tuple([bin10(x, 4) for x in terc])

            hsync = terc[0] & 1
            vsync = (terc[0] >> 1) & 1
            h2    = ((terc[0] >> 2) & 1)
            h3    = ((terc[0] >> 3) & 1)
            self.bch2 |= h2 << self.count
            self.bch3 |= h3 << self.count
            for d in range(4):
                self.bch[d] |= ((terc[1] >> d) & 1) << (2 * self.count)
                self.bch[d] |= ((terc[2] >> d) & 1) << (2 * self.count + 1)
            self.count += 1
            if self.count == 32:
                # print('BCH2', hex(self.bch2), hex(self.bch3)) # ecc24(self.bch2 & 0xffffff) == (self.bch2 >> 24))
                self.handle_island()
                self.bch2 = 0
                self.bch3 = 0
                self.bch = [0,0,0,0]
                self.count = 0
            rgb = (32 + 32 * h2, ) * 3
            # d = 'TERC %d' % ((terc[0] >> 3) & 1)
        elif self.in_video_data:
            (r,g,b) = [tmds_table[x] for x in ch]
            d = 'video (%02x, %02x, %02x)' % (r, g, b)
            # rgb = tuple([0xc0 + c // 64 for c in (r, g, b)])
            rgb = (r, g, b)
            (hsync, vsync) = (0, 0)
        d = '%-24s [ VSYNC %d HSYNC %d]' % (d, vsync, hsync)
        self.window = self.window[-10:]
        if self.window == 'DDDDDDDDdd':
            # print("----")
            self.in_data_island = True
            self.window = ''
        if self.window == 'dd':
            self.in_data_island = False
        if self.window.endswith('vv'):
            self.in_video_data = True

        (r, g, b) = rgb
        # r = min(255, r + 60 * vsync)
        # b = min(255, b + 60 * hsync)
        self.rgb.append((r, g, b))
        return d

    def im(self):
        (w, h) = (800, 525)
        (w, h) = (1650, 750)
        frame = self.rgb[:w * h]
        rgb = np.array(frame).astype(np.uint8).reshape((h, w, 3))
        return Image.fromarray(rgb, "RGB")

if __name__ == "__main__":
    vv = [int(l, 16) for l in open(sys.argv[1])][:]
    d = Decoder()
    for i,v in enumerate(vv):
        ch = [v & 0x3ff, (v >> 10) & 0x3ff, (v >> 20) & 0x3ff]
        # print()
        # sys.stdout.write("%6d: " % i)
        # print("%5d: %s" % (i, d.datum(ch)))
        d.datum(ch)
    d.im().save("out.png")
    print(d.regen_clock)
