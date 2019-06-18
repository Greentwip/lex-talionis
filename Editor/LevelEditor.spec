# -*- mode: python -*-

block_cipher = None

import sys
sys.modules['FixTk'] = None

a = Analysis(['LevelEditor.py'],
             pathex=['.'],
             binaries=[],
             datas=[('EditorCode', 'EditorCode'),
                    ('AutotileTemplates', 'AutotileTemplates')],
             hiddenimports=['pygame', '../Code/GlobalConstants', '../Code/Engine', '../Code/SaveLoad', '../Code/imagesDict', 'xml.etree.ElementTree'],
             hookspath=[],
             runtime_hooks=[],
             excludes=['FixTk', 'tcl', 'tk', '_tkinter', 'tkinter', 'Tkinter'],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

Key = ['mkl','libopenblas']

def remove_from_list(input, keys):
    outlist = []
    for item in input:
        name, _, _ = item
        flag = 0
        for key_word in keys:
            if name.find(key_word) > -1:
                flag = 1
        if flag != 1:
            outlist.append(item)
    return outlist

a.binaries = remove_from_list(a.binaries, Key)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='LevelEditor',
          debug=False,
          strip=False,
          upx=True,
          console=True,
          icon='editor_icon.ico' )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Editor')
