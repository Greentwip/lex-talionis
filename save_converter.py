import cPickle as pickle
# In order to use, must comment out all imports in Code.UnitObject.py
# Save obj converter
fp = 'SaveState2.p'
with open(fp, 'rb') as loadFile:
    saveObj = pickle.load(loadFile)

unit_info = saveObj['allunits']
for unit in unit_info:
    print(unit['name'])
    print(unit['stats'])
    print(unit['growths'])
    unit['stats'] = [(int(round(stat[0]*2/3)), stat[1]) if index != 9 else (stat[0]/2, stat[1]) for index, stat in enumerate(unit['stats'])]
    unit['growths'] = [int(round((growth/5)*2/3))*5 for growth in unit['growths']]
    if unit['movement_group'] == 1:
        unit['movement_group'] = 4
    elif unit['movement_group'] == 2:
        unit['movement_group'] = 1
    print(unit['stats'])
    print(unit['growths'])

with open('Fixed' + fp, 'wb') as saveFile:
    pickle.dump(saveObj, saveFile)