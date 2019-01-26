import os, glob
name = 'Light0_'
fps = glob.glob('*.png')
[os.rename(f, name + str(i) + '.png') for i, f in enumerate(fps)]
