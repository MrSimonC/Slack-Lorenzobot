# -*- mode: python -*-

block_cipher = None
requests_files = Tree(r'C:\Python35\Lib\site-packages\requests', prefix='requests')
slack_files = Tree(r'C:\Python35\Lib\site-packages\slackclient', prefix='slackclient')
websocket = Tree(r'C:\Python35\Lib\site-packages\websocket', prefix='websocket')
data_files = [('triage_rota.csv', 'triage_rota.csv', 'DATA')]
data_files += [('back office queue count.csv', 'back office queue count.csv', 'DATA')]
data_files += [('back office queue list.txt', 'back office queue list.txt', 'DATA')]

a = Analysis(['slack_lorenzobot.py'],
             pathex=['C:\\simon_files_compilation_zone\\slack_lorenzobot'],
             binaries=None,
             datas=None,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          requests_files,
          slack_files,
          websocket,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='slack_lorenzobot',
          debug=False,
          strip=False,
          upx=True,
          console=True )
coll = COLLECT(exe,
			data_files,
            upx=True,
			name='remedy')