import ijson
import os

dirname = os.path.dirname(__file__)
InFile = os.path.join(dirname, r'test2.json')

tablist = []
tabfields = {}


with open(InFile, 'rb') as input_file:
    parser = ijson.parse(input_file)
    tabfieldlist = []
    box = ""

    for prefix, event, value in parser:
            if event == 'start_array':
                if box != "":
                    tabfields[box] = list(set(tabfieldlist))
                if prefix =="":
                    box = "Contract"
                else:
                    box = prefix
                    box = box.replace("item.",'')
                tablist.append(box)
                tablist = list(set(tablist))
            if event == 'map_key':
                if value not in tablist:   
                    tabfieldlist.append(value)
                    tabfieldlist = list(set(tabfieldlist))

for tab in tabfields:
    for field in tabfields[tab]:
        if field in tablist:
            tabfields[tab].remove(field)

print(tabfields)
"""
    for prefix, event, value in parser:
            print('prefix={}, event={}, value={}'.format(prefix, event, value))
"""        
