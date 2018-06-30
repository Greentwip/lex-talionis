#! /usr/bin/env python2.7

import os, sys
sys.path.append('../../')

import Code.Engine as Engine
# So that the code basically starts looking in the parent directory
Engine.engine_constants['home'] = '../../'
import Code.GlobalConstants as GC
# Makes Gifs of Animations
import Code.BattleAnimation as BattleAnimation
import Code.MenuFunctions as MenuFunctions
import Code.Image_Modification as Image_Modification

class DummyItem(object):
    def __init__(self, kind, rng=None):
        self.TYPE = [kind]
        self.RNG = rng if rng else [1]
        self.spritetype = kind

class Animator(object):
    def __init__(self, klass, gender, name, item):
        self.unit = None  # Dummy unit object since we probably don't need it
        if item:
            magic = any([t in item.TYPE for t in ('Anima', 'Dark', 'Light')])
        else:
            magic = False
        anim = GC.ANIMDICT.partake(klass, gender, item, magic)
        if anim:
            # Build animation
            script = anim['script']
            frame_dir = anim['images'][name]
            anim = BattleAnimation.BattleAnimation(self.unit, frame_dir, script, name, item)
            anim.awake(owner=self, parent=None, partner=None, right=True, at_range=False) # Stand
        self.anim = anim
        self.anim_offset = 120

        # For darken backgrounds and drawing
        self.darken_background = 0
        self.target_dark = 0
        self.darken_ui_background = 0
        self.foreground = MenuFunctions.Foreground()
        self.combat_surf = Engine.create_surface((GC.WINWIDTH, GC.WINHEIGHT), transparent=True)

        self.counter = 1
        self.timer = 0

        self.klass, self.gender, self.name, self.item = klass, gender, name, item
        self.pose = 'Stand'
        self.outcom = 0
        self.def_damag = 0

    def flash_color(self, num_frames, fade_out=0, color=(248, 248, 248)):
        self.foreground.flash(num_frames, fade_out, color)

    def darken(self):
        self.target_dark += 4

    def lighten(self):
        self.target_dark -= 4

    def darken_ui(self):
        self.darken_ui_background = 1

    def lighten_ui(self):
        self.darken_ui_background = -3

    def outcome(self):
        return self.outcom

    def def_damage(self):
        return self.def_damag

    def shake(self, num):
        pass

    def platform_shake(self):
        pass

    def start_hit(self, sound=True, miss=False):
        if self.outcome() or self.def_damage() != 0:
            self.timer = 10

    def start_anim(self, pose):
        self.pose = pose
        if self.pose == 'Attack':
            self.outcom = 1
            self.def_damag = 1
        elif self.pose == 'Miss':
            self.outcom = 0
            self.def_damag = 0
        elif self.pose == 'Critical':
            self.outcom = 2
            self.def_damag = 3
        else:
            self.outcom = 0
            self.def_damag = 0
        self.counter = 1
        self.anim.start_anim(pose)

    def update(self):
        proceed = self.anim.can_proceed()
        if self.timer > 0:
            self.timer -= 1
        if proceed and self.timer == 0:
            self.anim.resume()
        self.anim.update()

    def draw(self):
        surf = Engine.create_surface((GC.WINWIDTH, GC.WINHEIGHT), transparent=True)
        Engine.fill(surf, (128, 160, 128))
        if self.darken_background or self.target_dark:
            bg = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['BlackBackground'], 100 - abs(int(self.darken_background * 12.5)))
            surf.blit(bg, (0, 0))
            if self.target_dark > self.darken_background:
                self.darken_background += 1
            elif self.target_dark < self.darken_background:
                self.darken_background -= 1

        # Make combat surf
        combat_surf = Engine.copy_surface(self.combat_surf)

        if self.darken_ui_background:
            self.darken_ui_background = min(self.darken_ui_background, 4)
            # bg = Image_Modification.flickerImageTranslucent(GC.IMAGESDICT['BlackBackground'], 100 - abs(int(self.darken_ui_background*11.5)))
            color = 255 - abs(self.darken_ui_background * 24)
            Engine.fill(combat_surf, (color, color, color), None, Engine.BLEND_RGB_MULT)
            # combat_surf.blit(bg, (0, 0))
            self.darken_ui_background += 1

        surf.blit(combat_surf, (0, 0))

        self.anim.draw_under(surf, (0, 0))
        self.anim.draw(surf, (0, 0))
        self.anim.draw_over(surf, (0, 0))

        self.foreground.draw(surf)

        return surf

    def save_surf(self, surf):
        image_name = ''.join([self.klass, str(self.gender), '_', self.name, '_', 
                              self.pose, '_', str(self.counter), '.png'])
        Engine.save_surface(surf, image_name)
        self.counter += 1
        return image_name
    
    def get_front_name(self):
        image_name = ''.join([self.klass, str(self.gender), '_', self.name, '_', 
                              self.pose])
        return image_name

animator = Animator('Sentinel', 0, 'GenericBlue', DummyItem('Axe'))
animator.start_anim('Attack')
filenames = []
while not animator.anim.done():
    animator.update()
    surf = animator.draw()
    filenames.append(animator.save_surf(surf))

# Now make a gif out of images
import imageio
images = []
for filename in filenames:
    images.append(imageio.imread(filename))
imageio.mimsave(animator.get_front_name() + '.gif', images, fps=50)
