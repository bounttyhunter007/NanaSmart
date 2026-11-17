"""Gera PNG de alta resolução e SVG a partir dos modelos centrais do projeto.

Executar na raiz com .venv/Scripts/python.exe DOCS/Diagrama_Classes_Slide/fontes/gerar.py
Requer Pillow. Não importa Django nem acessa o banco.
"""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1]
W, H, SCALE = 2400, 1670, 2
NAVY, ORANGE, INK, MUTED = '#102844', '#E58136', '#203249', '#53677D'
BORDER, LINE = '#A6B7C9', '#536F8E'
im = Image.new('RGB', (W*SCALE, H*SCALE), 'white')
d = ImageDraw.Draw(im)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<title>NanaSmart — Diagrama de classes principais</title>',
       '<desc>Nove classes de domínio e suas principais associações, com atributos selecionados e cardinalidades verificadas nos modelos Django.</desc>',
       f'<rect width="{W}" height="{H}" fill="white"/>']

def font(size, bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/' + ('arialbd.ttf' if bold else 'arial.ttf'), round(size*SCALE))

def rect(x, y, w, h, fill, stroke=None, width=2):
    d.rectangle([round(x*SCALE), round(y*SCALE), round((x+w)*SCALE), round((y+h)*SCALE)], fill=fill, outline=stroke, width=round(width*SCALE))
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke or "none"}" stroke-width="{width}"/>')

def text(x, y, value, size=30, color=INK, bold=False, anchor='start'):
    f = font(size, bold)
    px = x*SCALE
    if anchor == 'middle': px -= d.textlength(value, font=f)/2
    if anchor == 'end': px -= d.textlength(value, font=f)
    d.text((px, y*SCALE), value, font=f, fill=color, anchor='lt')
    svg.append(f'<text x="{x}" y="{y}" dominant-baseline="text-before-edge" font-family="Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}">{escape(value)}</text>')

def line(points, color=LINE, width=3):
    d.line([(round(x*SCALE), round(y*SCALE)) for x,y in points], fill=color, width=round(width*SCALE), joint='curve')
    svg.append(f'<polyline points="{" ".join(f"{x},{y}" for x,y in points)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')

def label(x, y, value, size=27, color=MUTED):
    tw = d.textlength(value, font=font(size))/SCALE
    rect(x-tw/2-9, y-5, tw+18, size+12, 'white')
    text(x, y, value, size, color, anchor='middle')

def card(x, y, name, attrs):
    rect(x, y, 620, 310, 'white', BORDER, 2.5)
    rect(x, y, 620, 82, NAVY)
    rect(x, y, 7, 82, ORANGE)
    text(x+310, y+23, name, 34, 'white', True, 'middle')
    for i, a in enumerate(attrs):
        assert d.textlength(a, font=font(30))/SCALE < 570, a
        text(x+26, y+109+i*46, a, 30)

rect(70, 32, 7, 76, ORANGE)
text(98, 30, 'Diagrama de classes', 48, NAVY, True)
text(100, 90, 'Classes principais e relacionamentos', 28, MUTED)
text(2330, 49, 'NanaSmart', 36, NAVY, True, 'end')

# Associações desenhadas antes das classes; sem setas de fluxo ou heranças fictícias.
line([(690,325),(890,325)])
line([(1510,325),(1710,325)])
line([(380,480),(380,680)])
line([(1200,480),(1200,680)])
line([(1510,835),(1710,835)])
line([(380,990),(380,1190)])
line([(1200,990),(1200,1190)])
line([(690,1345),(890,1345)])
line([(890,410),(790,410),(790,1090),(570,1090),(570,1190)])
line([(550,1500),(550,1560),(2020,1560),(2020,1500)])

card(70,170,'Empresa',[
    '+ nome: str', '+ cnpj: str', '+ email: str', '+ telefone: str'])
card(890,170,'Equipamento',[
    '+ nome: str', '+ numero_serie: str', '+ horimetro: float', '+ criticidade: str'])
card(1710,170,'PlanoManutencao',[
    '+ nome_servico: str', '+ intervalo_horas: float', '+ prioridade: str', '+ ativo: bool'])
card(70,680,'Usuario',[
    '+ username: str', '+ email: str', '+ tipo_usuario: str', '+ cargo: str'])
card(890,680,'Sensor',[
    '+ nome: str', '+ tipo: str', '+ unidade_medida: str', '+ limite_alerta: float'])
card(1710,680,'Telemetria',[
    '+ valor: float', '+ timestamp: datetime'])
card(70,1190,'OrdemServico',[
    '+ titulo: str', '+ tipo_os: str', '+ status: str', '+ prioridade: str'])
card(890,1190,'Alerta',[
    '+ tipo_alerta: str', '+ origem: str', '+ nivel: str', '+ status: str'])
card(1710,1190,'HistoricoManutencao',[
    '+ data_execucao: date', '+ custo_pecas: Decimal', '+ custo_mao_de_obra: Decimal', '+ /custo_total: Decimal'])

# Multiplicidades junto à classe que quantificam.
for x,y,v in [(715,345,'1'),(846,345,'0..*'),
               (1535,345,'1'),(1668,345,'0..*'),
               (426,501,'0..1'),(426,632,'0..*'),
               (1240,501,'1'),(1240,632,'0..*'),
               (1535,855,'1'),(1668,855,'0..*'),
               (426,1011,'0..1'),(426,1142,'0..*'),
               (1255,1011,'0..1'),(1255,1142,'0..*'),
               (730,1365,'0..1'),(848,1365,'0..*'),
               (860,435,'1'),(620,1142,'0..*'),
               (585,1515,'1'),(1960,1515,'0..1')]:
    label(x,y,v,27,INK)

for x,y,v in [(790,282,'possui'),(1610,282,'possui'),
               (380,563,'vincula'),(1200,563,'possui'),
               (1610,792,'registra'),(380,1073,'é responsável'),
               (1200,1073,'origina'),(790,1302,'atende'),
               (790,1042,'recebe O.S.'),(1570,1543,'registra execução')]:
    label(x,y,v,27)

text(70,1622,'1  um     0..1  opcional     0..*  zero ou muitos',26,MUTED)
text(2330,1622,'Visão resumida • atributos selecionados • / = derivado',26,MUTED,anchor='end')
svg.append('</svg>')
(OUT/'NanaSmart_Diagrama_Classes.svg').write_text('\n'.join(svg), encoding='utf-8')
im.save(OUT/'NanaSmart_Diagrama_Classes.png', dpi=(300,300), optimize=True)
im.resize((1200,835), Image.Resampling.LANCZOS).save(OUT/'fontes'/'previa.png')
print('Gerados: PNG 4800 × 3340 px e SVG vetorial.')
