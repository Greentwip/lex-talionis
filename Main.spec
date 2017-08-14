# -*- mode: python -*-

block_cipher = None


a = Analysis(['main.py'],
             pathex=['C:\\Users\\Patrick\\Documents\\Github\\lex-talionis'],
             binaries=[],
             datas=[('Data', 'Data'),
                    ('Audio', 'Audio'),
                    ('Saves/save_storage.txt', 'Saves'),
                    ('Sprites', 'Sprites'),
                    ('Code', 'Code')],
             hiddenimports=['Code/*.pyd'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='lion_throne',
          debug=False,
          strip=False,
          upx=True,
          console=True,
          icon='main_icon.ico' )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='the_lion_throne')
