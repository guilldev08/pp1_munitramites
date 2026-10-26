from pathlib import Path

ruta = Path('static/css/app.css')
texto = ruta.read_text(encoding='utf-8')
nuevo = Path('_scratch/chat_section.css').read_text(encoding='utf-8')

inicio = texto.index('/* --- Chatbot ------------------------------------------------------------ */')
fin = texto.index('/* --- Vacio -------------------------------------------------------------- */')

resultado = texto[:inicio] + nuevo + texto[fin:]
ruta.write_text(resultado, encoding='utf-8', newline='\n')
print('reemplazado', inicio, fin)
