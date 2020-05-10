# bmpfont.py
# By Paul Sidorsky - Freeware
# Updated by rainlash May 2016, January 2017, January 2019

"""Provides support for bitmapped fonts using pygame.

Font Index File Descrption

bmpfont lets you define where each character is within the bitmap,
along with some other options.  This lets you use a bitmap of any
dimension with characters of any size.  The file where the position
of each character is defined is called the font index file.  It is
a simple text file that may contain the lines listed below.
Whitespace is ignored, but the keywords are case-sensitive.
NOTE:  Blank lines and comments are not allowed!

width x
height y
- Specifies the dimensions of a character, in pixels.  Each
  character must be of the same width and height.  width defaults
  to 8 and height to 16 if omitted.

transrgb r g b
- Specifies the colour being used to indicate transparency.  If you
  don't wish to use transparency, set this to an unused colour.
  Defaults to black (0, 0, 0) if omitted.

alluppercase
- If present, indicates the font only has one case of letters which
  are specified in the index using upper case letters.  Strings
  rendered with BmpFont.blit() will be converted automatically.  If
  omitted, the font is assumed to have both cases of letters.
alllowercase
- If present, indicates the font only has one case of letters which
  are specified in the index using lower case letters.  Otherwise
  performs akin to 'alllowercase' option.

- All other lines are treated as character index specifiers with
  the following format:

  char x y w

  - char is the character whose position is being specified.  It
    can also be "space" (without quotes) to define a position for
    the space character.
  - x is the column number where char is located.  The position
    within the bitmap will be x * width (where width is specified
    above).
  - y is the row number where char is located.  The position will
    be y * height.
  - w is the width of the char itself in pixels. For instance, "i"
    might have a width of 1, while "c" might have a width of 4. 
"""

__all__ = ["BmpFont"]

from . import Engine

class BmpFont:
    """Provides an object for treating a bitmap as a font."""

    # Constructor - creates a BmpFont object.
    # Parameters:  name - Name of the font.
    def __init__(self, name):
        # Setup default values.
        self.alluppercase = False
        self.alllowercase = False
        self.stacked = False
        self.chartable = {}
        self.idxfile = Engine.engine_constants['home'] + "Sprites/Fonts/" + name.split('_')[0] + '.idx'
        self.bmpfile = Engine.engine_constants['home'] + "Sprites/Fonts/" + name + '.png'
        self.space_offset = 0
        self.width = 8
        self.height = 16
        self.transrgb = (0, 0, 0)
        self.memory = {}

        # Read the font index.  File errors will bubble up to caller.
        f = open(self.idxfile, encoding='utf-8', mode="r")

        for x in f.readlines():
            # Remove EOL, if any.
            if x[-1] == '\n':
                x = x[:-1]
            words = x.split()

            # Handle keywords.              
            if words[0] == "alluppercase":
                self.alluppercase = True
            elif words[0] == "alllowercase":
                self.alllowercase = True
            elif words[0] == 'stacked':
                self.stacked = True
            elif words[0] == 'space_offset':
                self.space_offset = int(words[1])
            elif words[0] == "width":
                self.width = int(words[1])
            elif words[0] == "height":
                self.height = int(words[1])
            elif words[0] == "transrgb":
                self.transrgb = (int(words[1]), int(words[2]), int(words[3]))
            else:  # Default to index entry.
                if words[0] == "space":
                    words[0] = ' '
                if self.alluppercase:
                    words[0] = words[0].upper()
                if self.alllowercase:
                    words[0] = words[0].lower()
                self.chartable[words[0]] = (int(words[1]) * self.width,
                                            int(words[2]) * self.height,
                                            int(words[3]))
        f.close()

        # Setup the actual bitmap that holds the font graphics.
        self.surface = Engine.image_load(self.bmpfile)
        Engine.set_colorkey(self.surface, self.transrgb, rleaccel=True)

    # blit() - Copies a string to a surface using the bitmap font.
    # Parameters:  string    - The message to render.  All characters
    #                          must have font index entries or a
    #                          KeyError will occur.
    #              surf      - The pygame surface to blit string to.
    #              pos       - (x, y) location specifying location
    #                          to copy to (within surf).  Meaning
    #                          depends on usetextxy parameter.
    #              usetextxy - If true, pos refers to a character cell
    #                          location.  For example, the upper-left
    #                          character is (0, 0), the next is (0, 1),
    #                          etc.  This is useful for screens with
    #                          lots of text.  Cell size depends on the
    #                          font width and height.  If false, pos is
    #                          specified in pixels, allowing for precise
    #                          text positioning.
    def blit(self, string, surf, pos=(0, 0), usetextxy=False):
        """Draw a string to a surface using the bitmapped font."""
        def normal_render(x):
            # Render the font.
            for c in string:
                if c not in self.memory:
                    try:
                        char_pos_x = self.chartable[c][0]
                        char_pos_y = self.chartable[c][1]
                        char_width = self.chartable[c][2]
                    except KeyError as e:
                        char_pos_x = 0
                        char_pos_y = 0
                        char_width = 4
                        print(e)
                        print("%s is not chartable"%(c))
                        print('string', string)
                    subsurf = Engine.subsurface(self.surface, (char_pos_x, char_pos_y, self.width, self.height))
                    self.memory[c] = (subsurf, char_width)
                else:
                    subsurf, char_width = self.memory[c]
                Engine.blit(surf, subsurf, (x, y))
                # surf.blit(self.surface, (x, y), ((char_pos_x, char_pos_y), (self.width, self.height))) # subsurface
                x += char_width + self.space_offset

        def stacked_render(x):
            orig_x = x
            for c in string:
                if c not in self.memory:

                    try:
                        char_pos_x = self.chartable[c][0]
                        char_pos_y = self.chartable[c][1]
                        char_width = self.chartable[c][2]
                    except KeyError as e:
                        char_pos_x = 0
                        char_pos_y = 0
                        char_width = 4
                        print(e)
                        print("%s is not chartable"%(c))
                        print('string', string)

                    highsurf = Engine.subsurface(self.surface, (char_pos_x, char_pos_y, self.width, self.height))
                    print(char_pos_x, char_pos_y + self.height, self.width, self.height)
                    print(self.surface.get_width(), self.surface.get_height())
                    lowsurf = Engine.subsurface(self.surface, (char_pos_x, char_pos_y + self.height, self.width, self.height))
                    self.memory[c] = (highsurf, lowsurf, char_width)
            for c in string:
                highsurf, lowsurf, char_width = self.memory[c]
                Engine.blit(surf, lowsurf, (x, y))
                x += char_width + self.space_offset
            for c in string:
                highsurf, lowsurf, char_width = self.memory[c]
                Engine.blit(surf, highsurf, (orig_x, y))
                orig_x += char_width + self.space_offset

        x, y = pos
        if usetextxy:
            x *= self.width
            y *= self.height
        surfwidth, surfheight = surf.get_size()

        # The commented out line is INCREDIBLY slow.
        # NOT NECESSARY IF WE USE RGBA 
        # fontsurf = self.surface.convert_alpha(surf)
        # fontsurf = self.surface

        if self.alluppercase:
            string = string.upper()
        if self.alllowercase:
            string = string.lower()
        string = string.replace('_', ' ')

        if self.stacked:
            stacked_render(x)
        else:
            normal_render(x)

    # size() - Returns the length and height of a string (height will always be self.height)
    # Parameters:  string     - the string that is to be measured. All characters must
    #                           have font index entries or a KeyError will occur.
    def size(self, string):
        """Returns the length and width of a bitmapped string"""
        length = 0
        # height = self.height
        if self.alluppercase:
            string = string.upper()
        if self.alllowercase:
            string = string.lower()
        string = string.replace('_', ' ')
        for c in string:
            try:
                char_width = self.chartable[c][2]
            except KeyError as e:
                print(e)
                print("%s is not chartable"%(c))
                print("string", string)
                char_width = 4
            length += char_width
        return (length, self.height)
