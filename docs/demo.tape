# Renders docs/demo.gif against a fake BookStack API.  From the repo root:
#   python3 docs/demo/mock_bookstack.py &          # fake wiki on 127.0.0.1:16875
#   WIKI_URL=http://127.0.0.1:16875 WIKI_TOKEN_ID=demo WIKI_TOKEN_SECRET=demo vhs docs/demo.tape
# Assumes `wikitui` is on PATH (e.g. `uv tool install .` or the built binary).
Output docs/demo.gif
Set Shell "bash"
Set FontSize 16
Set Width 1200
Set Height 700
Set Padding 12
Set TypingSpeed 60ms

Type "wikitui" Enter
Sleep 3s
Down Sleep 600ms
Enter Sleep 1500ms
Down Sleep 600ms
Enter Sleep 1200ms
Down Sleep 500ms
Enter Sleep 3500ms
Right Sleep 3s
Right Sleep 3s
Type "/" Sleep 500ms
Type "deploy" Sleep 500ms
Enter Sleep 2500ms
Down@120ms 14 Sleep 700ms
Enter Sleep 3500ms
Type "b" Sleep 2s
Type "b" Sleep 1500ms
Type "q" Sleep 1s
