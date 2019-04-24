# Autotile maker part 2
import os
from collections import Counter
from PIL import Image

WIDTH, HEIGHT = 16, 16

def similar(p1, p2):
    return sum(i != j for i, j in zip(p1, p2))

def similar_fast(p1, p2, output=True):
    if p1 == p2:
        if output:
            print('0')
        return True
    return False

class Series(object):
    def __init__(self):
        self.series = []

    def append(self, palette):
        self.series.append(palette)
        assert len(self.series) <= 16

    def is_present(self, test):
        test_palette = test.palette
        all_palettes = [im.palette for im in self.series]
        for palette in all_palettes:
            if similar(test_palette, palette):
                return True
        return False

    def is_present_slow(self, test):
        if test.palette in [im.palette for im in self.series]:
            return True
        return False

class PaletteData(object):
    def __init__(self, arr):
        self.arr = arr
        self.data = list(arr.getdata()) 
        count = 1
        self.uniques = reduce(lambda l, x: l if x in l else l+[x], self.data, [])
        self.uniques = sorted(self.uniques, key=lambda x: self.data.count(x), reverse=True)
        self.palette = self.data[:]
        # self.simple_palette = self.data[:]
        for u in self.uniques:
            for index, pixel in enumerate(self.data):
                if pixel == u:
                    self.palette[index] = count
                # if pixel[2] > pixel[1] and pixel[2] > pixel[0]:
                #    self.simple_palette[index] = 1 # Blue
                # else:
                #    self.simple_palette[index] = 0 # Not really blue
            count += 1

def remove_bad_color(new):
    for i in range(WIDTH):
        for j in range(HEIGHT):
            color = new.getpixel((i, j))
            if color[0] == 8 and color[1] == 8 and color[2] == 8:
                adjacent_colors = Counter()
                for pos in [(i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)]:
                    if pos[0] >= 0 and pos[1] >=0 and pos[0] < 8 and pos[1] < 8:
                        adjacent_colors[new.getpixel(pos)] += 1
                most_common = adjacent_colors.most_common(1)[0][0]
                new.putpixel((i, j), most_common)
    return new

def color_change_band(new_images, series, palette, current, test_im, (x, y)):
    # Build color conversion dictionary
    color_conversion_dict = {}
    for index, color in enumerate(palette.data):
        color_conversion_dict[color] = test_im.data[index]

    # Now actually build new images
    for band in range(16):
        new = Image.new('RGB', (WIDTH, HEIGHT))
        for index, color in enumerate(series.series[band].data):
            new_color = color_conversion_dict.get(color, (8, 8, 8))
            new.putpixel((index%WIDTH, index/HEIGHT), new_color)
        # Now fix any that are black -- do it twice
        # new = remove_bad_color(remove_bad_color(new))
        new_images[band].paste(new, (x*WIDTH, y*HEIGHT))

def make_autotiles_from_image(fn, dir_out):
    autotile_templates = []
    for fp in sorted(os.listdir('.')):
        if fp.endswith('.png') and fp != 'MapSprite.png' and not fp.startswith('autotile'):
            autotile_templates.append(fp)

    print('Reading files %s...' %(len(autotile_templates)))
    books = []
    for template in autotile_templates:
        image = Image.open(template)
        width = image.size[0]/16
        number = width/WIDTH*image.size[1]/HEIGHT
        minitiles = [Series() for x in range(number)]
        print(width, image.size[1], number)
        for band in range(16):
            for x in range(width/WIDTH):
                for y in range(image.size[1]/HEIGHT):
                    palette = image.crop((band*width + x*WIDTH, y*HEIGHT, band*width + x*WIDTH + WIDTH, y*HEIGHT + HEIGHT))
                    minitiles[x + y*width/WIDTH].append(PaletteData(palette))
        assert all(len(series.series) == 16 for series in minitiles)
        books.append(minitiles)

    print('Making new files...')
    main = Image.open(fn)

    new_images = [Image.new('RGB', main.size) for _ in range(16)]
    print(main.size)

    print('Comparison...')
    for x in range(main.size[0]/WIDTH):
        for y in range(main.size[1]/HEIGHT):
            print(x, y)
            current = main.crop((x*WIDTH, y*HEIGHT, x*WIDTH + WIDTH, y*HEIGHT + HEIGHT))
            test_im = PaletteData(current)
            closest_series = None
            closest_palette = None
            min_sim = 400
            for book in books:
                for series in book:
                    for palette in series.series:
                        similarity = similar(palette.palette, test_im.palette)
                        if similarity < min_sim:
                            min_sim = similarity
                            closest_series = series
                            closest_palette = palette
            print(min_sim)
            if closest_series:
                color_change_band(new_images, closest_series, closest_palette, current, test_im, (x, y))

    print('Saving...')
    if not os.path.exists(dir_out):
        os.mkdir(dir_out)
    for idx, n in enumerate(new_images):
        n.save(dir_out + '/autotile' + str(idx) + '.png')
