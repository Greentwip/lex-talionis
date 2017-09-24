#! /usr/bin/env python2.7

# Next step is to given a large file, split it at silences and test each subsound
import glob, time, sys
from pydub import AudioSegment
import pygame

pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.init()
pygame.mixer.init()

pygame.display.set_mode((240, 160))

# Nominally 3
MILLISECONDS = 1
NOISE_FLOOR = 0.08
FOLDER = 'FE_Sounds/'
TEST_ME = 'CombatDeath.wav'

SFXDICT = {sfx: pygame.mixer.Sound(sfx) for sfx in glob.glob(FOLDER + '*.wav')}

def parse_song(song):
    length = len(song)
    max_db = song.max

    loudness = []
    for x in xrange(length):
        subsong = song[x*MILLISECONDS:(x+1)*MILLISECONDS]
        if subsong.max > max_db*NOISE_FLOOR:
            loudness.append(subsong.max)

    cascade = [t - s for s, t in zip(loudness, loudness[1:])]
    # # Get rid of long silences
    # new_cascade = []
    # for num in cascade:
    #     if num == 0 and new_cascade and new_cascade[-1] == 0:
    #         pass
    #     else:
    #         new_cascade.append(num)

    song_facts = {}
    song_facts['length'] = length
    song_facts['max_db'] = max_db
    song_facts['cascade'] = cascade
    song_facts['song'] = song
    return song_facts

# Create database
database = []
for fp in glob.glob(FOLDER + '*.wav'):
    print('Processing %s' % fp)
    match = AudioSegment.from_wav(fp)
    database.append((fp, parse_song(match)))

absolute_max = float(max([song['max_db'] for fp, song in database]))
print('Absolute Max %s' % absolute_max)
# Normalize
for fp, song in database:
    song['cascade'] = [c/absolute_max for c in song['cascade']]

to_test = AudioSegment.from_wav(TEST_ME)
my_song = pygame.mixer.Sound(TEST_ME)
print('Processing %s' % to_test)
print(to_test.frame_rate)
# # print(len(to_test))
# to_test = to_test + 5
# one_second_silence = AudioSegment.silent(duration=1000)
# to_test += one_second_silence
to_test_values = parse_song(to_test)
to_test_values['cascade'] = [c/absolute_max for c in to_test_values['cascade']]

# Comparison
for fp, song in database:
    # print(fp, song['length'], to_test_values['length'])
    # Don't worry about songs with drastically different lengths
    if abs(song['length'] - to_test_values['length']) > 1000:
        song['comp'] = 100
        continue
    if abs(len(song['cascade']) - len(to_test_values['cascade'])) > 200:
        song['comp'] = 100
        continue
    comp = sum([abs(i - j) for i, j in zip(song['cascade'], to_test_values['cascade'])])/float(len(to_test_values['cascade']))
    song['comp'] = comp
    # print(comp)
    # if abs(comp) < 0.02:
    #     print(fp, len(song['cascade']), len(to_test_values['cascade']))
    #     matches.append((fp, abs(comp)))

def terminate():
    pygame.mixer.music.stop()
    pygame.mixer.quit()
    pygame.quit()
    sys.exit()

def listen():
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            terminate()
        if event.type == pygame.KEYUP:
            if event.key == pygame.K_ESCAPE:
                terminate()

print('Matches:')
for fp, song in sorted(database, key=lambda x: x[1]['comp'])[:50]:
    listen()
    # my_song.play()
    # time.sleep(my_song.get_length() + 0.2)
    print('%s: %s' %(fp, song['comp']))
    SFXDICT[fp].play()
    time.sleep(SFXDICT[fp].get_length() + 0.2)
print('Done!')
