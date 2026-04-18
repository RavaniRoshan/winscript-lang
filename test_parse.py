from winscript.parser import parse
try:
    print(parse('set value of cell "B3" to 47\n'))
except Exception as e:
    print("ERROR:", e)
