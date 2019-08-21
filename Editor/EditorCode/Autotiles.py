# Autotile maker part 2
import os, sys
from collections import Counter, OrderedDict
from functools import reduce
from PyQt5.QtWidgets import QProgressDialog
from PyQt5.QtCore import QTimer
from PIL import Image

sys.path.append('../')
from Code.imagesDict import COLORKEY

WIDTH, HEIGHT = 16, 16

"""
Speeds:
MATLAB: 4.3 seconds 79 matches bad colors
SLOW: 1.5 seconds 47 matches bad colors
REGULAR: 0.32 seconds 27 matches
FAST: 0.01 seconds 24 matches
"""

def diff(seq):
    iterable = iter(seq)
    prev = next(iterable)
    for element in iterable:
        yield bool(element - prev)
        prev = element

def similar_slow(p1, p2):
    return sum(i != j for i, j in zip(diff(p1), diff(p2)))

def transpose_sorted(p):
    return [y for x, y in sorted(zip(range(WIDTH*WIDTH), p), key=lambda t: t[0]%WIDTH)]

def transpose_lc(p):
    return [p[i*WIDTH + j] for j in range(WIDTH) for i in range(WIDTH)]

def similar_matlab(p1, p2):
    # print(p1)
    p1_diff_row = [diff(row) for row in [p1[i*WIDTH:i*WIDTH+HEIGHT] for i in range(HEIGHT)]]
    p1_diff_row = [item for sublist in p1_diff_row for item in sublist]
    # print(p1_diff_row)
    transposed_p1 = transpose_lc(p1)
    # print(transposed_p1)
    p1_diff_col = [diff(col) for col in [transposed_p1[i*WIDTH:i*WIDTH+HEIGHT] for i in range(HEIGHT)]]
    p1_diff_col = [item for sublist in p1_diff_col for item in sublist]
    # print(p1_diff_col)
    # print(p2)
    p2_diff_row = [diff(row) for row in [p2[i*WIDTH:i*WIDTH+HEIGHT] for i in range(HEIGHT)]]
    p2_diff_row = [item for sublist in p2_diff_row for item in sublist]
    # print(p2_diff_row)
    transposed_p2 = transpose_lc(p2)
    # print(transposed_p2)
    p2_diff_col = [diff(col) for col in [transposed_p2[i*WIDTH:i*WIDTH+HEIGHT] for i in range(HEIGHT)]]
    p2_diff_col = [item for sublist in p2_diff_col for item in sublist]
    # print(p2_diff_col)
    row_diff = similar(p1_diff_row, p2_diff_row)
    col_diff = similar(p1_diff_col, p2_diff_col)
    # print(row_diff, col_diff)
    return row_diff + col_diff

def similar(p1, p2):
    return sum(i != j for i, j in zip(p1, p2))

def similar_fast(p1, p2):
    return 0 if p1 == p2 else WIDTH*HEIGHT

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
                    if similar_fast(f.palette, map_tile.palette):
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
            new.putpixel((index%WIDTH, index//HEIGHT), new_color)
        # Now fix any that are black -- do it twice
        # new = remove_bad_color(remove_bad_color(new))
        autotile_frames[band].paste(new, (x*WIDTH, y*HEIGHT))

class AutotileMaker(object):
    def __init__(self, map_sprite_fn, dir_out, window):
        self.map_sprite_fn = map_sprite_fn
        self.dir_out = dir_out
        self.window = window

        self.running = True

        self.autotile_templates = self.gather_autotile_templates()
        self.books = []
        self.now_an_autotile = []

        # Set up progress Dialog
        msg = "Generating Autotiles..."
        self.progress_dlg = QProgressDialog(msg, "Cancel", 0, 100, window)
        self.progress_dlg.setAutoClose(True)
        self.progress_dlg.setWindowTitle(msg)
        self.progress_dlg.canceled.connect(self.cancel)
        self.progress_dlg.show()
        self.progress_dlg.setValue(0)

        # === Timing ===
        self.main_timer = QTimer()
        self.main_timer.timeout.connect(self.tick)
        self.main_timer.start(1)  # 120 FPS

        self.next_autotile_template = list(reversed(self.autotile_templates))
        self.state = 1

    def tick(self):
        if self.running:
            self.update_step()
        else:
            self.main_timer.stop()

    def cancel(self):
        self.running = False

    def complete(self):
        self.running = False
        # When complete
        self.window.set_image(self.dir_out + '/MapSprite.png')
        self.window.autotiles.clear()
        auto_loc = self.dir_out + '/Autotiles/'
        self.window.autotiles.load(auto_loc)

    def gather_autotile_templates(self):
        autotile_templates = []        
        for fp in sorted(os.listdir('AutotileTemplates')):
            if fp.endswith('.png') and fp != 'MapSprite.png' and not fp.startswith('autotile'):
                print(fp)
                autotile_templates.append(fp)
        return autotile_templates

    def update_step(self):
        if self.state == 1:  # Load autotile templates
            if self.next_autotile_template:
                template = self.next_autotile_template.pop()
                idx = len(self.autotile_templates) - 1 - len(self.next_autotile_template)
                self.read_autotile_template(template)
                self.progress_dlg.setValue(int(20*idx/len(self.autotile_templates)))
            else:
                self.state = 2

        elif self.state == 2:  # Create new images
            print('Making new files...')
            self.map_sprite = Image.open(self.map_sprite_fn)

            self.autotile_frames = [Image.new('RGB', self.map_sprite.size, COLORKEY) for _ in range(16)]
            print(self.map_sprite.size)
            self.state = 3

        elif self.state == 3:
            print('Comparison...')
            self.map_tiles = OrderedDict()
            for x in range(self.map_sprite.size[0] // WIDTH):
                for y in range(self.map_sprite.size[1] // HEIGHT):
                    tile = self.map_sprite.crop((x*WIDTH, y*HEIGHT, x*WIDTH + WIDTH, y*HEIGHT + HEIGHT))
                    tile_palette = PaletteData(tile)
                    self.map_tiles[(x, y)] = tile_palette
            self.next_map_tile = list(reversed(self.map_tiles.keys()))
            self.progress_dlg.setValue(25)
            self.state = 4

        elif self.state == 4:
            if self.next_map_tile:
                pos = self.next_map_tile.pop()
                idx = len(self.map_tiles) - 1 - len(self.next_map_tile)
                self.create_autotiles_from_image(pos)
                self.progress_dlg.setValue(25 + int(74*idx/len(self.map_tiles)))
            else:
                self.state = 5

        elif self.state == 5:
            print('Saving...')
            self.progress_dlg.setValue(99)
            # Fill spots with green
            for x, y in self.now_an_autotile:
                for i in range(WIDTH):
                    for j in range(HEIGHT):
                        self.map_sprite.putpixel((x*WIDTH + i, y*HEIGHT + j), COLORKEY)
            print(len(self.now_an_autotile))
            self.map_sprite.save(self.dir_out + '/MapSprite.png')
            if not os.path.exists(self.dir_out + '/Autotiles'):
                os.mkdir(self.dir_out + '/Autotiles')
            for idx, n in enumerate(self.autotile_frames):
                n.save(self.dir_out + '/Autotiles/autotile' + str(idx) + '.png')
            print('Done!')

            self.progress_dlg.setValue(100)
            self.complete()
            self.progress_dlg.hide()

    def read_autotile_template(self, fn):
        # Each autotile template becomes a book
        # A book contains a dictionary of positions as keys and series as values
        image = Image.open('AutotileTemplates/' + fn)
        width = image.size[0] // 16  # There are 16 frames 
        num_tiles_x = width // WIDTH
        num_tiles_y = image.size[1] // HEIGHT
        number = num_tiles_x*num_tiles_y
        minitiles = [Series() for _ in range(number)]
        for frame in range(16):  # There are 16 frames, stacked horizontally with one another
            x_offset = frame*width
            for x in range(num_tiles_x):
                for y in range(num_tiles_y):
                    palette = image.crop((x_offset + x*WIDTH, y*HEIGHT, x_offset + x*WIDTH + WIDTH, y*HEIGHT + HEIGHT))
                    minitiles[x + y*num_tiles_x].append(PaletteData(palette))
        assert all(len(series.series) == 16 for series in minitiles)
        self.books.append(minitiles)

    def create_autotiles_from_image(self, pos):
        x, y = pos
        print(x, y)
        # e1 = time.time()
        tile_palette = self.map_tiles[(x, y)]
        closest_series = None
        closest_frame = None
        closest_book = None
        min_sim = 16
        # min_sim = 2*WIDTH*(WIDTH-1)/16
        for bidx, book in enumerate(self.books):
            for sidx, series in enumerate(book):
                for fidx, frame in enumerate(series.series):
                    similarity = similar_fast(frame.palette, tile_palette.palette)
                    if similarity < min_sim:
                        min_sim = similarity
                        print(min_sim)
                        closest_series = series
                        closest_frame = frame
                        closest_book = book
                        print(bidx, sidx, fidx)
        if closest_series:
            color_change_band(self.map_tiles, self.autotile_frames, closest_book, closest_series, closest_frame, tile_palette, (x, y))
            self.now_an_autotile.append((x, y))
        # print(time.time() - e1)
