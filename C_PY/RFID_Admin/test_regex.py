import re
import config

with open('config.py', 'r', encoding='utf-8') as f:
    contenido = f.read()
print('Original len:', len(contenido))

str_areas = 'AREAS = {\n    "1": "Test"\n}\n'
res = re.sub(r'AREAS\s*=\s*\{.*?\}(?=\n|$)', str_areas, contenido, flags=re.DOTALL)
print('Modified len:', len(res))
if contenido == res:
    print('REGEX FAILED TO MATCH AREAS')
else:
    print('REGEX MATCHED AREAS')

str_tablas = 'AREAS_TABLAS = {\n    "1": "Test"\n}\n'
res2 = re.sub(r'AREAS_TABLAS\s*=\s*\{.*?\}(?=\n|$)', str_tablas, res, flags=re.DOTALL)
if res == res2:
    print('REGEX FAILED TO MATCH AREAS_TABLAS')
else:
    print('REGEX MATCHED AREAS_TABLAS')
