import os
name = 'Rune'
[os.rename(f, name + str(i) + '.png') for i, f in enumerate(os.listdir('.')) if f.endswith('.png')]
