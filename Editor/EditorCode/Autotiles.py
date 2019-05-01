# Autotile maker part 2
import os, sys
from collections import Counter, OrderedDict
from PIL import Image

sys.path.append('../')
from Code.imagesDict import COLORKEY

WIDTH, HEIGHT = 16, 16

def similar_slow(p1, p2):
    p1_diff = [(1 if x[1] - x[0] else 0) for x in zip(p1[1:], p1)]
    p2_diff = [(1 if x[1] - x[0] else 0) for x in zip(p2[1:], p2)]
    return sum(i != j for i, j in zip(p1_diff, p2_diff))

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

    def is_present_fast(self, test):
        test_palette = test.palette
        all_palettes = [im.palette for im in self.series]
        for palette in all_palettes:
            if similar_fast(test_palette, palette, False):
                return True
        return False

    def is_present_slow(self, test):
        if test.palette in [im.palette for im in self.series]:
            return True
        return False

    def get_frames_with_color(self, color):
        return [im for im in self.series if color in im.colors]

class PaletteData(object):
    def __init__(self, arr):
        self.arr = arr
        self.colors = list(arr.getdata()) 
        self.uniques = reduce(lambda l, x: l if x in l else l+[x], self.colors, [])
        # Sort by most popular
        self.uniques = sorted(self.uniques, key=lambda x: self.colors.count(x), reverse=True)
        self.palette = self.colors[:]
        # self.simple_palette = self.data[:]
        """
        for idx, u in enumerate(self.uniques):
            for index, pixel in enumerate(self.data):
                if pixel == u:
                    # Each pixel in the palette is assigned its color id
                    self.palette[index] = idx + 1
                # if pixel[2] > pixel[1] and pixel[2] > pixel[0]:
                #    self.simple_palette[index] = 1 # Blue
                # else:
                #    self.simple_palette[index] = 0 # Not really blue
        """
        for index, pixel in enumerate(self.colors):
            # Each pixel in the palette is assigned its color id
            self.palette[index] = self.uniques.index(pixel)

def remove_bad_color(new):
    for i in range(WIDTH):
        for j in range(HEIGHT):
            color = new.getpixel((i, j))
            if color[0] == 8 and color[1] == 8 and color[2] == 8:
                adjacent_colors = Counter()
                for pos in [(i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)]:
                    if pos[0] >= 0 and pos[1] >= 0 and pos[0] < WIDTH and pos[1] < HEIGHT:
                        adjacent_colors[new.getpixel(pos)] += 1
                most_common = adjacent_colors.most_common(1)[0][0]
                new.putpixel((i, j), most_common)
    return new

# Changes the color of a band to match palette color of map
def color_change_band(map_tiles, autotile_frames, closest_book, closest_series,
                      closest_frame, tile, pos):
    x, y = pos
    # Converts colors from closest frame to tile
    color_conversion_dict = {}
    for index, color in enumerate(closest_frame.colors):
        color_conversion_dict[color] = tile.colors[index]

    # What colors are missing?
    def fix_missing_color(color):
        # Does that color show up in other frames in the autotile band?
        for series in closest_book:
            frames_with_color = series.get_frames_with_color(color)
            for f in frames_with_color:
                for map_tile in map_tiles.values():
                    # If so, do those frames show up in the map sprite?
                    if similar_fast(f.palette, map_tile.palette, False):
                        # If so, add the color conversion to the dict
                        color_index = f.colors.index(color)
                        new_color = map_tile.colors[color_index]
                        color_conversion_dict[color] = new_color
                        print("%s has become %s" % (color, new_color))
                        return

    for band in range(16):
        for index, color in enumerate(closest_series.series[band].colors):
            if color not in color_conversion_dict:
                print('Missing Color: %s' % str(color))
                fix_missing_color(color)

    # Now actually build new images
    for band in range(16):
        new = Image.new('RGB', (WIDTH, HEIGHT))
        for index, color in enumerate(closest_series.series[band].colors):
            new_color = color_conversion_dict.get(color, (8, 8, 8))
            new.putpixel((index%WIDTH, index/HEIGHT), new_color)
        # Now fix any that are black -- do it twice
        # new = remove_bad_color(remove_bad_color(new))
        autotile_frames[band].paste(new, (x*WIDTH, y*HEIGHT))

def create_autotiles_from_image(map_sprite_fn, dir_out):
    if not os.path.exists('AutotileTemplates'):
        print('Autotile templates are missing!')
        print('Make sure all autotile templates are located in "Editor/AutotileTemplates/')
        return
    
    # Otherwise
    autotile_templates = []        
    for fp in sorted(os.listdir('AutotileTemplates')):
        if fp.endswith('.png') and fp != 'MapSprite.png' and not fp.startswith('autotile'):
            print(fp)
            autotile_templates.append(fp)

    print('Reading %s autotile templates...' %(len(autotile_templates)))
    books = []  # Each autotile template becomes a book
    # A book contains a dictionary of positions as keys and series as values
    for template in autotile_templates:
        image = Image.open('AutotileTemplates/' + template)
        width = image.size[0]/16  # There are 16 frames 
        num_tiles_x = width/WIDTH
        num_tiles_y = image.size[1]/HEIGHT
        number = num_tiles_x*num_tiles_y
        minitiles = [Series() for _ in range(number)]
        for frame in range(16):  # There are 16 frames, stacked hoirzontally with one another
            x_offset = frame*width
            for x in range(num_tiles_x):
                for y in range(num_tiles_y):
                    palette = image.crop((x_offset + x*WIDTH, y*HEIGHT, x_offset + x*WIDTH + WIDTH, y*HEIGHT + HEIGHT))
                    minitiles[x + y*num_tiles_x].append(PaletteData(palette))
        assert all(len(series.series) == 16 for series in minitiles)
        books.append(minitiles)

    print('Making new files...')
    map_sprite = Image.open(map_sprite_fn)

    autotile_frames = [Image.new('RGB', map_sprite.size, COLORKEY) for _ in range(16)]
    print(map_sprite.size)

    print('Comparison...')
    map_tiles = OrderedDict()
    for x in range(map_sprite.size[0]/WIDTH):
        for y in range(map_sprite.size[1]/HEIGHT):
            tile = map_sprite.crop((x*WIDTH, y*HEIGHT, x*WIDTH + WIDTH, y*HEIGHT + HEIGHT))
            tile_palette = PaletteData(tile)
            map_tiles[(x, y)] = tile_palette

    now_an_autotile = []
    for x, y in map_tiles:
        print(x, y)
        tile_palette = map_tiles[(x, y)]
        closest_series = None
        closest_frame = None
        closest_book = None
        min_sim = WIDTH*HEIGHT/16
        for bidx, book in enumerate(books):
            for sidx, series in enumerate(book):
                for fidx, frame in enumerate(series.series):
                    similarity = similar(frame.palette, tile_palette.palette)
                    if similarity < min_sim:
                        min_sim = similarity
                        print(min_sim)
                        closest_series = series
                        closest_frame = frame
                        closest_book = book
                        print(bidx, sidx, fidx)
        if closest_series:
            color_change_band(map_tiles, autotile_frames, closest_book, closest_series, closest_frame, tile_palette, (x, y))
            now_an_autotile.append((x, y))

    print('Saving...')
    # Fill spots with green
    for x, y in now_an_autotile:
        print(x, y)
        for i in range(WIDTH):
            for j in range(HEIGHT):
                map_sprite.putpixel((x*WIDTH + i, y*HEIGHT + j), COLORKEY)
    map_sprite.save(dir_out + '/MapSprite.png')
    if not os.path.exists(dir_out):
        os.mkdir(dir_out)
    for idx, n in enumerate(autotile_frames):
        n.save(dir_out + '/Autotiles/autotile' + str(idx) + '.png')
    print('Done!')
