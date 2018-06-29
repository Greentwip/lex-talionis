# make a gif out of images
import glob
import imageio
fps = 2
filenames = glob.glob('autotile*.png')
print(filenames)
images = []
for filename in filenames:
    images.append(imageio.imread(filename))
imageio.mimsave('output.gif', images, fps=fps)
