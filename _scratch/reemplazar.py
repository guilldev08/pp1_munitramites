from pathlib import Path

ruta = Path('static/js/app.js')
texto = ruta.read_text(encoding='utf-8')
nuevo = Path('_scratch/chat_section.js').read_text(encoding='utf-8')

inicio = texto.index('  /* --------------------------------------------------------------------\n     Chatbot: pestaña emergente + barra de la portada')
fin = texto.index('  /* --------------------------------------------------------------------\n     Tema claro / oscuro')

resultado = texto[:inicio] + nuevo + texto[fin:]
ruta.write_text(resultado, encoding='utf-8', newline='\n')
print('reemplazado', inicio, fin)
