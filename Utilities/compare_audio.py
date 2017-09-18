#! /usr/bin/env python2.7

# Next step is to given a large file, split it at silences and test each subsound
import glob
from pydub import AudioSegment

MILLISECONDS = 3
NOISE_FLOOR = 0.08
FOLDER = 'FE_Sounds/'
TEST_ME = 'save.wav'

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
print('Processing %s' % to_test)
print(to_test.frame_rate)
# # print(len(to_test))
# to_test = to_test + 5
# one_second_silence = AudioSegment.silent(duration=1000)
# to_test += one_second_silence
to_test_values = parse_song(to_test)
to_test_values['cascade'] = [c/absolute_max for c in to_test_values['cascade']]

# Comparison
matches = []
for fp, song in database:
    # print(fp, song['length'], to_test_values['length'])
    # Don't worry about songs with drastically different lengths
    if abs(song['length'] - to_test_values['length']) > 1000:
        continue
    if abs(len(song['cascade']) - len(to_test_values['cascade'])) > 50:
        continue
    comp = sum([abs(i - j) for i, j in zip(song['cascade'], to_test_values['cascade'])])/float(len(to_test_values['cascade']))
    # print(comp)
    if abs(comp) < 0.02:
        print(fp, len(song['cascade']), len(to_test_values['cascade']))
        matches.append((fp, abs(comp)))

print('Matches:')
for fp, confidence in sorted(matches, key=lambda x: x[1]):
    print('%s: %s' %(fp, confidence))
print('Done!')
