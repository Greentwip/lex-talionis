try:
    import GlobalConstants as GC
    import Image_Modification, Engine
except ImportError:
    from . import GlobalConstants as GC
    from . import Image_Modification, Engine

class MovingBackground(object):
    def __init__(self, BGSurf):
        self.lastBackgroundUpdate = Engine.get_time()
        self.change_counter = 0
        self.backgroundCounter = 0
        self.BGSurf = BGSurf

    def draw(self, surf):
        self.change_counter += 1
        if self.change_counter > 2:
            self.change_counter = 0
        if self.change_counter == 0:
            self.backgroundCounter += 1
            if self.backgroundCounter >= self.BGSurf.get_width():
                self.backgroundCounter = 0
        
        # Clip the Background surface based on how much it needs to be moved
        BG1Sub = (self.backgroundCounter, 0, min(self.BGSurf.get_width() - self.backgroundCounter, GC.WINWIDTH), GC.WINHEIGHT)
        BG1Surf = Engine.subsurface(self.BGSurf, BG1Sub)

        # Determine if we need a second section of the background surface to fill up the rest of the background
        if BG1Surf.get_width() < GC.WINWIDTH:
            BG2Sub = (0, 0, min(self.BGSurf.get_width() - BG1Surf.get_width(), GC.WINWIDTH), GC.WINHEIGHT)
            BG2Surf = Engine.subsurface(self.BGSurf, BG2Sub)
            surf.blit(BG2Surf, (BG1Surf.get_width(), 0))
        surf.blit(BG1Surf, (0, 0))

class StaticBackground(object):
    def __init__(self, BGSurf, fade=True):
        self.BGSurf = BGSurf
        if fade:
            self.fade = 100
            self.state = "In"
        else:
            self.fade = 0
            self.state = "Neutral"

    def draw(self, surf):
        if self.state == "In":
            self.fade -= 4
            BGSurf = Image_Modification.flickerImageTranslucent(self.BGSurf, self.fade)
            if self.fade <= 0:
                self.fade = 0
                self.state = "Neutral"
        elif self.state == "Out":
            self.fade += 4
            BGSurf = Image_Modification.flickerImageTranslucent(self.BGSurf, self.fade)
            if self.fade >= 100:
                return True
        else:
            BGSurf = self.BGSurf
        surf.blit(BGSurf, (0, 0))
        return False

    def fade_out(self):
        self.state = "Out"

class MovieBackground(object):
    def __init__(self, movie_prefix, speed=125, loop=True, fade_out=False):
        self.counter = 0
        self.movie_prefix = movie_prefix
        self.num_frames = len([image_name for image_name in GC.IMAGESDICT if image_name.startswith(movie_prefix)])

        self.last_update = Engine.get_time()
        self.speed = speed
        self.loop = loop
        self.fade_out = fade_out

    def draw(self, surf):
        image = GC.IMAGESDICT[self.movie_prefix + str(self.counter)]
        if self.fade_out:
            progress = float(self.counter)/self.num_frames
            transparency = int(100*progress)
            image = Image_Modification.flickerImageTranslucent(image, transparency)
        surf.blit(image, (0, 0))

        if Engine.get_time() - self.last_update > self.speed:
            self.counter += 1
            self.last_update = Engine.get_time()
            if self.counter >= self.num_frames:
                if self.loop:
                    self.counter = 0
                else:
                    return 'Done'

class Foreground(object):
    def __init__(self):
        self.foreground = None
        self.foreground_frames = 0
        self.fade_out = False
        self.fade_out_frames = 0

    def flash(self, num_frames, fade_out, color=(248, 248, 248)):
        self.foreground_frames = num_frames
        self.foreground = GC.IMAGESDICT['BlackBackground'].copy()
        Engine.fill(self.foreground, color)
        self.fade_out_frames = fade_out

    def draw(self, surf, blend=False):
        # Screen flash
        if self.foreground or self.fade_out_frames:
            if self.fade_out:
                alpha = 100 - self.foreground_frames/float(self.fade_out_frames)*100
                foreground = Image_Modification.flickerImageTranslucent(self.foreground, alpha)
            else:
                foreground = self.foreground
            # Always additive blend
            Engine.blit(surf, foreground, (0, 0), blend=Engine.BLEND_RGB_ADD)
            self.foreground_frames -= 1
            # If done
            if self.foreground_frames <= 0:
                if self.fade_out_frames and not self.fade_out:
                    self.foreground_frames = self.fade_out_frames
                    self.fade_out = True
                else:
                    self.fade_out_frames = 0
                    self.foreground_frames = 0
                    self.foreground = None
                    self.fade_out = False
