#! usr/bin/env python

# Line formatter uses Image

from PIL import Image

passive_fp = 'playerDragoonM.png'
active_fp = 'playerDragoonM_move.png'

active = Image.open(active_fp)
passive = Image.open(passive_fp)

new_p = Image.new("RGB", [192, 144], (128,160,128))
new_a = Image.new("RGB", [192, 160], (128,160,128))

p1 = passive.crop((0, 0, 16, 32))
p2 = passive.crop((0, 32, 16, 32*2))
p3 = passive.crop((0, 32*2, 16, 32*3))

l1 = active.crop((0, 0, 32, 32))
l2 = active.crop((0, 32, 32, 32+32))
l3 = active.crop((0, 32*2, 32, 32+32*2))
l4 = active.crop((0, 32*3, 32, 32+32*3))

d1 = active.crop((0, 32*4, 32, 32+32*4))
d2 = active.crop((0, 32*5, 32, 32+32*5))
d3 = active.crop((0, 32*6, 32, 32+32*6))
d4 = active.crop((0, 32*7, 32, 32+32*7))

u1 = active.crop((0, 32*8, 32, 32+32*8))
u2 = active.crop((0, 32*9, 32, 32+32*9))
u3 = active.crop((0, 32*10, 32, 32+32*10))
u4 = active.crop((0, 32*11, 32, 32+32*11))

f1 = active.crop((0, 32*12, 32, 32+32*12))
f2 = active.crop((0, 32*13, 32, 32+32*13))
f3 = active.crop((0, 32*14, 32, 32+32*14))

new_p.paste(p1, (24, 8))
new_p.paste(p2, (24+64, 8))
new_p.paste(p3, (24+64*2, 8))

new_p.paste(f1, (16, 8+96))
new_p.paste(f2, (16+64, 8+96))
new_p.paste(f3, (16+64*2, 8+96))

new_a.paste(d1, (8, 8))
new_a.paste(d2, (8+48, 8))
new_a.paste(d3, (8+48*2, 8))
new_a.paste(d4, (8+48*3, 8))

new_a.paste(l1, (8, 48))
new_a.paste(l2, (8+48, 48))
new_a.paste(l3, (8+48*2, 48))
new_a.paste(l4, (8+48*3, 48))

new_a.paste(l1.transpose(Image.FLIP_LEFT_RIGHT), (8, 88))
new_a.paste(l2.transpose(Image.FLIP_LEFT_RIGHT), (8+48, 88))
new_a.paste(l3.transpose(Image.FLIP_LEFT_RIGHT), (8+48*2, 88))
new_a.paste(l4.transpose(Image.FLIP_LEFT_RIGHT), (8+48*3, 88))

new_a.paste(u1, (8, 128))
new_a.paste(u2, (8+48, 128))
new_a.paste(u3, (8+48*2, 128))
new_a.paste(u4, (8+48*3, 128))

new_a.save("fixed_" + active_fp)
new_p.save("fixed_" + passive_fp)