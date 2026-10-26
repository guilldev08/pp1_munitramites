import importlib.util
import shutil

print('pdftotext', shutil.which('pdftotext'))
for name in ('pypdf', 'PyPDF2', 'fitz', 'pdfminer'):
    print(name, importlib.util.find_spec(name))
