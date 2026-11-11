"""Gera os itens 3, 4 e 5 do template: PDF vetorial, PNG e diagrams.net.

Executar na raiz: .venv/Scripts/python.exe DOCS/Diagramas_UML_2_5/fontes/gerar_diagramas.py
Requer ReportLab; a exportação PNG utiliza pdftoppm (Poppler) no PATH.
Não importa a aplicação nem consulta ou modifica o banco de dados.
"""
from pathlib import Path
from math import atan2, cos, sin, pi
import html
import subprocess
import xml.etree.ElementTree as ET

from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape, A3

OUT = Path(__file__).resolve().parents[1]
W, H = 1600, 1050
INK, MUTED, BLUE, BORDER = '#203249', '#52677D', '#2867A6', '#9BB3C9'
LIGHT, PALE, GREEN, LILAC = '#EFF5FB', '#F7FAFD', '#EDF7F3', '#F2EFF9'
for name, file in [('Nana', 'arial.ttf'), ('Nana-Bold', 'arialbd.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(Path('C:/Windows/Fonts') / file)))
pdfmetrics.registerFontFamily('Nana', normal='Nana', bold='Nana-Bold', italic='Nana', boldItalic='Nana-Bold')


class Diagram:
    def __init__(self, number, title, subtitle):
        self.number, self.title = number, title
        self.ops = []
        self.rect(0, 0, W, H, '#FFFFFF', '#FFFFFF')
        self.rect(46, 40, 8, 67, BLUE, BLUE)
        self.text(76, 44, f'{number}. {title}', 34, bold=True)
        self.text(76, 91, subtitle, 17, MUTED)
        self.text(1535, 52, 'NanaSmart', 19, BLUE, True, 'right')
        self.text(1535, 84, 'UML 2.5 | 11/11/2026', 13, MUTED, align='right')

    def rect(self, x, y, w, h, fill='#FFFFFF', stroke=BORDER, width=1.5, dash=False):
        self.ops.append(('rect', x, y, w, h, fill, stroke, width, dash))

    def text(self, x, y, value, size=17, color=INK, bold=False, align='left'):
        for n, line in enumerate(value.split('\n')):
            self.ops.append(('text', x, y + n * size * 1.35, line, size, color, bold, align))

    def line(self, points, color=MUTED, width=1.7, dash=False, arrow=False):
        self.ops.append(('line', points, color, width, dash, arrow))

    def circle(self, x, y, radius, fill='#FFFFFF', stroke=BLUE, width=2):
        self.ops.append(('circle', x, y, radius, fill, stroke, width))

    def poly(self, points, fill, stroke=BORDER, width=1.5):
        self.ops.append(('poly', points, fill, stroke, width))

    def label(self, x, y, value, size=14, color=MUTED, align='center'):
        lines = value.split('\n')
        width = max(pdfmetrics.stringWidth(t, 'Nana', size) for t in lines) + 14
        rx = x - width / 2 if align == 'center' else x
        self.rect(rx, y - 3, width, len(lines) * size * 1.35 + 4, '#FFFFFF', '#FFFFFF', 0)
        self.text(x, y, value, size, color, align=align)

    def package(self, x, y, w, h, name, body='', fill=LIGHT, fontsize=16):
        tab = min(w - 22, max(100, pdfmetrics.stringWidth(name, 'Nana-Bold', 18) + 30))
        self.rect(x, y + 23, w, h - 23, fill, BLUE)
        self.rect(x, y, tab, 29, fill, BLUE)
        self.text(x + 14, y + 5, name, 18, BLUE, True)
        if body:
            self.text(x + 16, y + 46, body, fontsize)

    def component(self, x, y, w, h, name, body='', fill=LIGHT):
        self.rect(x, y, w, h, fill, BLUE)
        self.rect(x + w - 34, y + 14, 20, 30, fill, BLUE)
        self.rect(x + w - 40, y + 19, 12, 7, '#FFFFFF', BLUE)
        self.rect(x + w - 40, y + 33, 12, 7, '#FFFFFF', BLUE)
        self.text(x + 15, y + 15, name, 19, BLUE, True)
        if body:
            self.text(x + 15, y + 52, body, 16)

    def node(self, x, y, w, h, stereotype, title, fill=LIGHT):
        d = 13
        self.poly([(x,y),(x+d,y-d),(x+w+d,y-d),(x+w,y)], '#E4EDF6')
        self.poly([(x+w,y),(x+w+d,y-d),(x+w+d,y+h-d),(x+w,y+h)], '#DBE6F1')
        self.rect(x, y, w, h, fill, BLUE)
        self.text(x+15, y+12, f'«{stereotype}»', 14, MUTED)
        self.text(x+15, y+36, title, 19, BLUE, True)

    def artifact(self, x, y, w, h, name, body=''):
        self.rect(x,y,w,h,'#FFFFFF',BORDER)
        self.poly([(x+w-27,y+9),(x+w-16,y+9),(x+w-10,y+15),(x+w-10,y+30),(x+w-27,y+30)], '#FFFFFF')
        self.line([(x+w-16,y+9),(x+w-16,y+15),(x+w-10,y+15)], BORDER, 1)
        self.text(x+12,y+9,'«artifact»',13,MUTED)
        self.text(x+12,y+31,name,16,INK,True)
        if body:
            self.text(x+12,y+58,body,14)

    def assembly(self, start, end, title, provider='right', label_y=None):
        """Esfera fornecida e cavidade requerida concêntricas, com hastes."""
        x1,y = start
        x2,_ = end
        cx = (x1+x2)/2
        if provider == 'right':
            self.line([(cx+8,y),(x2,y)],BLUE,2)
            self.line([(x1,y),(cx-14,y)],BLUE,2)
            angles = [pi/2+i*pi/32 for i in range(33)]
        else:
            self.line([(x1,y),(cx-8,y)],BLUE,2)
            self.line([(cx+14,y),(x2,y)],BLUE,2)
            angles = [-pi/2+i*pi/32 for i in range(33)]
        self.circle(cx,y,8)
        self.line([(cx+14*cos(a),y+14*sin(a)) for a in angles],BLUE,2)
        self.label(cx, label_y if label_y is not None else y-42, title,13)

    def footer(self, first, second):
        self.line([(55,934),(1545,934)],BORDER,1)
        self.text(60,950,first,15,MUTED)
        self.text(60,978,second,15,MUTED)
        self.text(1540,1020,f'{self.number}.1. Modelo | 1/2',12,MUTED,align='right')

    def draw_pdf(self, c):
        pw, ph = landscape(A3)
        margin = 20
        scale = min((pw-2*margin)/W,(ph-2*margin)/H)
        c.saveState()
        c.translate((pw-W*scale)/2,(ph-H*scale)/2)
        c.scale(scale,scale)
        for op in self.ops:
            kind,*a=op
            c.setDash()
            if kind=='rect':
                x,y,w,h,fill,stroke,lw,dash=a
                c.setFillColor(HexColor(fill)); c.setStrokeColor(HexColor(stroke)); c.setLineWidth(lw)
                if dash: c.setDash(7,5)
                c.rect(x,H-y-h,w,h,fill=1,stroke=1 if lw else 0)
            elif kind=='text':
                x,y,value,size,color,bold,align=a
                c.setFont('Nana-Bold' if bold else 'Nana',size); c.setFillColor(HexColor(color))
                fn={'left':c.drawString,'center':c.drawCentredString,'right':c.drawRightString}[align]
                fn(x,H-y-size*.83,value)
            elif kind=='line':
                pts,color,lw,dash,arrow=a
                c.setStrokeColor(HexColor(color)); c.setLineWidth(lw)
                if dash: c.setDash(7,5)
                p=c.beginPath(); p.moveTo(pts[0][0],H-pts[0][1])
                for x,y in pts[1:]: p.lineTo(x,H-y)
                c.drawPath(p)
                if arrow:
                    c.setDash(); (px,py),(x,y)=pts[-2:]; theta=atan2(y-py,x-px)
                    q=c.beginPath()
                    for i,ang in enumerate((theta+.45,theta-.45)):
                        ax,ay=x-12*cos(ang),y-12*sin(ang)
                        if i==0: q.moveTo(ax,H-ay); q.lineTo(x,H-y)
                        else: q.lineTo(ax,H-ay)
                    c.drawPath(q)
            elif kind=='circle':
                x,y,r,fill,stroke,lw=a
                c.setFillColor(HexColor(fill)); c.setStrokeColor(HexColor(stroke)); c.setLineWidth(lw)
                c.circle(x,H-y,r,fill=1,stroke=1)
            elif kind=='poly':
                pts,fill,stroke,lw=a
                c.setFillColor(HexColor(fill)); c.setStrokeColor(HexColor(stroke)); c.setLineWidth(lw)
                p=c.beginPath(); p.moveTo(pts[0][0],H-pts[0][1])
                for x,y in pts[1:]: p.lineTo(x,H-y)
                p.close(); c.drawPath(p,fill=1,stroke=1)
        c.restoreState()

    def save_drawio(self, path):
        mx=ET.Element('mxfile',host='app.diagrams.net',version='24.7.17')
        dg=ET.SubElement(mx,'diagram',id=f'nana-{self.number}',name=self.title)
        model=ET.SubElement(dg,'mxGraphModel',dx='1600',dy='1050',grid='1',gridSize='10',page='1',pageScale='1',pageWidth=str(W),pageHeight=str(H),math='0',shadow='0')
        rt=ET.SubElement(model,'root'); ET.SubElement(rt,'mxCell',id='0'); ET.SubElement(rt,'mxCell',id='1',parent='0')
        uid=1
        def vertex(x,y,w,h,style,value=''):
            nonlocal uid
            uid+=1
            cell=ET.SubElement(rt,'mxCell',id=str(uid),value=value,style=style,vertex='1',parent='1')
            ET.SubElement(cell,'mxGeometry',x=str(x),y=str(y),width=str(w),height=str(h),attrib={'as':'geometry'})
        def edge(pts,color,width,dash=False,arrow=False):
            nonlocal uid
            uid+=1
            style=f'edgeStyle=none;rounded=0;html=1;strokeColor={color};strokeWidth={width};endArrow={"open" if arrow else "none"};endFill=0;'
            if dash: style+='dashed=1;dashPattern=7 5;'
            cell=ET.SubElement(rt,'mxCell',id=str(uid),style=style,edge='1',parent='1')
            geo=ET.SubElement(cell,'mxGeometry',relative='1',attrib={'as':'geometry'})
            ET.SubElement(geo,'mxPoint',x=str(pts[0][0]),y=str(pts[0][1]),attrib={'as':'sourcePoint'})
            ET.SubElement(geo,'mxPoint',x=str(pts[-1][0]),y=str(pts[-1][1]),attrib={'as':'targetPoint'})
            if len(pts)>2:
                ar=ET.SubElement(geo,'Array',attrib={'as':'points'})
                for x,y in pts[1:-1]: ET.SubElement(ar,'mxPoint',x=str(x),y=str(y))
        for kind,*a in self.ops:
            if kind=='rect':
                x,y,w,h,fill,stroke,lw,dash=a
                vertex(x,y,w,h,f'rounded=0;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke if lw else "none"};strokeWidth={lw};dashed={int(dash)};')
            elif kind=='text':
                x,y,value,size,color,bold,align=a
                tw=max(1,pdfmetrics.stringWidth(value,'Nana-Bold' if bold else 'Nana',size)+4)
                x=x-tw/2 if align=='center' else x-tw if align=='right' else x
                vertex(x,y,tw,size*1.3,f'text;html=1;whiteSpace=wrap;overflow=visible;strokeColor=none;fillColor=none;fontFamily=Arial;fontSize={size};fontColor={color};fontStyle={int(bold)};align={align};verticalAlign=top;spacing=0;',html.escape(value))
            elif kind=='line': edge(*a)
            elif kind=='circle':
                x,y,r,fill,stroke,lw=a
                vertex(x-r,y-r,r*2,r*2,f'ellipse;html=1;fillColor={fill};strokeColor={stroke};strokeWidth={lw};')
            elif kind=='poly':
                pts,fill,stroke,lw=a
                # Faces dos nós e símbolo de documento: polígonos editáveis via stencil.
                import base64
                x=min(p[0] for p in pts); y=min(p[1] for p in pts)
                w=max(p[0] for p in pts)-x; h=max(p[1] for p in pts)-y
                st=ET.Element('shape',w='100',h='100',aspect='variable',strokewidth='inherit')
                fg=ET.SubElement(st,'foreground'); path_el=ET.SubElement(fg,'path')
                for i,(px,py) in enumerate(pts): ET.SubElement(path_el,'move' if i==0 else 'line',x=str((px-x)/max(w,1)*100),y=str((py-y)/max(h,1)*100))
                ET.SubElement(path_el,'close'); ET.SubElement(fg,'fillstroke')
                # diagrams.net usa raw-DEFLATE + base64 para stencils embutidos.
                import zlib
                co=zlib.compressobj(wbits=-15)
                packed=base64.b64encode(co.compress(ET.tostring(st))+co.flush()).decode()
                vertex(x,y,w,h,f'shape=stencil({packed});fillColor={fill};strokeColor={stroke};strokeWidth={lw};')
        ET.indent(mx)
        ET.ElementTree(mx).write(path,encoding='utf-8',xml_declaration=True)


def packages():
    d=Diagram(3,'Diagrama de Pacotes UML','3.1. Modelo | Organização lógica dos módulos e principais dependências')
    d.package(60,175,330,140,'FrontATT','Interface web Vue 3\nindex.html, app.js, styles.css')
    d.package(635,175,330,140,'app','Configuração Django\nsettings.py e urls.py')
    d.package(1210,175,330,140,'scripts','Seed e simulação de leituras\nExecução via Django / ORM')
    d.package(60,460,330,340,'Acesso','«agrupamento lógico»',PALE)
    d.package(82,545,286,100,'authentication','Login, perfil e senha',fontsize=15)
    d.package(82,690,286,88,'accounts','Empresa, Usuario e permissões',fontsize=14)
    d.line([(225,645),(225,690)],dash=True,arrow=True)
    d.package(500,420,600,430,'Operação','«agrupamento lógico»',PALE)
    d.package(525,510,245,115,'ativos','Equipamentos, planos\ne criticidade ABC',fontsize=15)
    d.package(835,510,240,170,'manutencao','Ordens e históricos',fontsize=15)
    d.package(852,598,206,63,'dashboards','Indicadores e resumo',fill='#FFFFFF',fontsize=13)
    d.package(525,730,245,100,'telemetria','Sensores, leituras, tendências',fontsize=14)
    d.package(835,730,240,100,'alertas','Ocorrências e evidências',fontsize=14)
    d.package(1210,460,330,340,'Integrações e saídas','«agrupamento lógico»',PALE)
    d.package(1232,545,286,100,'gemini_api','Contexto, prompts e Gemini',fill=LILAC,fontsize=15)
    d.package(1232,690,286,88,'exportacao','Relatórios CSV, Excel e PDF',fill=GREEN,fontsize=15)
    d.line([(390,245),(635,245)],dash=True,arrow=True)
    d.label(510,204,'consome API REST',15)
    d.line([(690,315),(690,366),(225,366),(225,460)],dash=True,arrow=True)
    d.label(430,344,'configura rotas',14)
    d.line([(800,315),(800,420)],dash=True,arrow=True)
    d.label(800,358,'registra apps',14)
    d.line([(910,315),(910,366),(1375,366),(1375,460)],dash=True,arrow=True)
    d.label(1150,344,'configura rotas',14)
    d.line([(1210,285),(1152,285),(1152,440),(1100,440)],dash=True,arrow=True)
    d.label(1152,395,'usa',13)
    d.line([(500,690),(435,690),(435,735),(390,735)],dash=True,arrow=True)
    d.label(435,646,'empresa /\npermissões',13)
    d.line([(1100,550),(1210,550)],dash=True,arrow=True)
    d.label(1155,506,'usa IA',13)
    d.line([(1210,745),(1160,745),(1160,818),(1100,818)],dash=True,arrow=True)
    d.label(1155,769,'consulta',13)
    d.line([(647,730),(647,625)],dash=True,arrow=True)
    d.label(647,680,'equipamento',13)
    d.line([(770,780),(835,780)],dash=True,arrow=True)
    d.label(802,743,'gera',13)
    d.line([(956,730),(956,680)],dash=True,arrow=True)
    d.label(1016,693,'vincula OS',12)
    d.line([(835,555),(770,555)],dash=True,arrow=True)
    d.label(802,524,'usa',12)
    d.line([(770,606),(805,606),(805,643),(835,643)],dash=True,arrow=True)
    d.label(804,671,'horímetro',12)
    d.footer('Seta tracejada: dependência do cliente para o fornecedor. Exibidas as relações principais, com ciclos do código preservados.',
             'Acesso, Operação e Integrações e saídas são agrupamentos lógicos; os demais nomes correspondem a pastas reais do repositório.')
    return d


def components():
    d=Diagram(4,'Diagrama de Componentes UML','4.1. Modelo | Componentes lógicos de um único backend Django')
    d.component(55,305,310,210,'Interface web','FrontATT / Vue 3\nTelas operacionais, gráficos\ne cliente HTTP com JWT')
    d.component(525,180,590,645,'API NanaSmart','Django REST Framework\nRoteamento: app/urls.py | Persistência e políticas compartilhadas',PALE)
    d.component(550,335,245,105,'Identidade e acesso','accounts + authentication')
    d.component(845,335,245,105,'Gestão de ativos','ativos',GREEN)
    d.component(550,505,245,115,'Monitoramento','telemetria + alertas')
    d.component(845,505,245,115,'Manutenção','manutencao + dashboards',GREEN)
    d.component(550,705,245,90,'Exportação','exportacao',GREEN)
    d.component(845,705,245,90,'Assistente de IA','gemini_api',LILAC)
    d.component(1265,265,280,240,'Persistência','Django ORM\nDriver psycopg2\n\nModelos dos apps\nBanco PostgreSQL')
    d.component(1265,680,280,140,'Google Gemini','«serviço externo»\nAPI de geração de conteúdo',LILAC)
    d.assembly((365,400),(525,400),'INanaSmartREST',label_y=357)
    d.label(445,427,'HTTP / JSON + JWT',12)
    d.assembly((1115,400),(1265,400),'IPersistenciaORM',label_y=357)
    d.assembly((795,562),(845,562),'IOrdemServico',label_y=636)
    d.assembly((1090,750),(1265,750),'IGeracaoConteudo',label_y=710)
    # Relações internas de uso, sem transformar os módulos em serviços remotos.
    d.line([(967,505),(967,440)],dash=True,arrow=True)
    d.label(1004,463,'usa ativos',12)
    d.line([(550,562),(506,562),(506,385),(550,385)],dash=True,arrow=True)
    d.label(490,477,'políticas',12)
    d.line([(795,750),(820,750),(820,675),(967,675),(967,620)],dash=True,arrow=True)
    d.label(975,647,'consulta manutenção',13)
    d.footer('Esfera: interface fornecida. Cavidade: interface requerida. Conexão esfera/cavidade: contrato utilizado entre componentes.',
             'INanaSmartREST reúne as rotas /api/*. Interfaces são nomes conceituais dos contratos existentes; os módulos internos executam no mesmo processo.')
    return d


def deployment():
    d=Diagram(5,'Diagrama de Implantação','5.1. Modelo | Cenário local documentado no repositório')
    d.node(55,225,1040,660,'device','Estação local de desenvolvimento',PALE)
    d.node(85,325,330,250,'executionEnvironment','Navegador web')
    d.artifact(103,408,292,140,'FrontATT/','index.html, app.js, styles.css\nlive-chart.js\nAbertura local de index.html')
    d.node(555,325,500,250,'executionEnvironment','Python + Django runserver')
    d.text(572,389,'127.0.0.1:9000 | app.settings',14,MUTED)
    d.artifact(573,425,464,125,'Backend Django','manage.py, app/ e apps de negócio\nDRF, JWT, signals e serviços de domínio\nIntegração opcional: GEMINI_API_KEY')
    d.node(85,665,330,180,'executionEnvironment','Python CLI (opcional)')
    d.artifact(103,733,292,94,'simulador_realtime.py','scripts/ | usa os modelos Django')
    d.node(555,665,500,180,'executionEnvironment','PostgreSQL')
    d.artifact(573,739,464,88,'Banco: manutencao','Tabelas e índices criados pelas migrations')
    d.node(1220,225,310,205,'node','CDN externa',GREEN)
    d.text(1236,296,'cdnjs.cloudflare.com',16)
    d.text(1236,327,'Vue 3, jsPDF, AutoTable, XLSX\nDependências carregadas\npelo navegador via HTTPS.',15)
    d.node(1220,665,310,180,'node','Google Gemini',LILAC)
    d.text(1236,737,'API gerenciada de IA\nRequer acesso à internet\ne chave de API no backend.',15)
    d.line([(415,470),(555,470)],BLUE,2)
    d.label(485,414,'HTTP REST\nTCP 9000\nJSON / JWT',13)
    d.line([(805,575),(805,665)],BLUE,2)
    d.label(919,606,'SQL / TCP 5432\npsycopg2',14)
    d.line([(415,781),(555,781)],BLUE,2)
    d.label(485,731,'SQL / TCP\n5432',13)
    d.line([(415,365),(455,365),(455,300),(1155,300),(1155,327),(1220,327)],BLUE,2)
    d.label(850,278,'HTTPS / TCP 443 - bibliotecas JavaScript',14)
    d.line([(1055,495),(1145,495),(1145,765),(1220,765)],BLUE,2)
    d.label(1190,566,'HTTPS\nTCP 443\nSDK google-genai',13)
    d.footer('Caminhos de comunicação: linhas contínuas, com protocolo e porta. Os ambientes locais podem compartilhar a mesma máquina.',
             'O simulador grava pelo ORM e aciona os signals reais. A integração com sensores físicos não está especificada no código analisado.')
    return d


STYLE = ParagraphStyle('body',fontName='Nana',fontSize=10.6,leading=15,textColor=HexColor(INK),spaceAfter=9)
SMALL = ParagraphStyle('small',parent=STYLE,fontSize=8.2,leading=11,spaceAfter=0)


def p(text, style=STYLE):
    return Paragraph(text,style)


def draw_paragraph(c, text, x, y, width, style=STYLE):
    para=p(text,style)
    _,h=para.wrap(width,2000)
    para.drawOn(c,x,y-h)
    return y-h-style.spaceAfter


def heading(c, text, x, y, size=14):
    c.setFont('Nana-Bold',size); c.setFillColor(HexColor(BLUE)); c.drawString(x,y,text)
    return y-24


def details(c, number):
    c.setPageSize(A4)
    pw,ph=A4
    left,right=44,44
    y=ph-47
    titles={3:'3.2. Memória Descritiva',4:'4.2. Mapeamento de Interfaces',5:'5.2. Infraestrutura de Execução'}
    y=heading(c,titles[number],left,y,19)
    y=draw_paragraph(c,'NanaSmart | Modelagem Arquitetural UML 2.5 | Complemento ao modelo da página anterior.',left,y,pw-left-right,SMALL)-17
    if number==3:
        lines=[
            'FrontATT concentra a apresentação em Vue 3 e consome as rotas REST do backend.',
            'app compõe o sistema por configurações, registro de aplicações e roteamento HTTP.',
            'Acesso agrupa authentication e accounts: identidade, empresas, perfis e permissões.',
            'Operação reúne ativos, manutencao, telemetria e alertas por responsabilidade de negócio.',
            'dashboards permanece em manutencao e consolida indicadores e resumos operacionais.',
            'Telemetria utiliza equipamentos e gera alertas por limites e por análise de tendências.',
            'Alertas acionam os serviços de manutenção para criar ou vincular ordens de serviço.',
            'Ativos e manutenção possuem dependências recíprocas, inclusive pelo horímetro.',
            'Integrações e saídas reúne gemini_api e exportacao, que consultam dados operacionais.',
            'As referências à IA em ativos e manutenção impedem classificá-las como camadas isoladas.',
            'scripts fornece carga inicial e simulação, reutilizando configurações e modelos Django.',
            'Serviços, serializers, políticas e o adapter Gemini delimitam responsabilidades.',
            'A visibilidade usa módulos Python públicos; não há restrição formal de importação por camada.',
            'O acesso aos dados é controlado por autenticação, perfil e filtros de empresa na API.',
            'Os três agrupamentos lógicos do desenho não representam novos diretórios físicos.',
        ]
        # Exatamente 15 linhas de memória descritiva, conforme limite do template.
        for line in lines:
            assert pdfmetrics.stringWidth(line,'Nana',9.0)<pw-left-right
            c.setFont('Nana',9); c.setFillColor(HexColor(INK)); c.drawString(left,y-9,line); y-=15
        y-=25
        y=heading(c,'Leitura das dependências',left,y)
        y=draw_paragraph(c,'A seta tracejada parte do pacote que utiliza uma funcionalidade e aponta para seu fornecedor. O desenho seleciona dependências relevantes para a arquitetura; não é um inventário de todos os imports. A relação FrontATT → app representa consumo em execução da API configurada por app.',left,y,pw-left-right)
        y=heading(c,'Correspondência com o repositório',left,y-10)
        y=draw_paragraph(c,'Configuração: app/settings.py e app/urls.py. Negócio: modelos, views, serviços e signals de ativos/, manutencao/, telemetria/ e alertas/. Integração: gemini_api/context_service.py, adapters.py e exportacao/views.py. Interface: FrontATT/index.html e app.js.',left,y,pw-left-right)
    elif number==4:
        y=draw_paragraph(c,'As interfaces abaixo nomeiam contratos conceituais já oferecidos pelas rotas, serviços ou bibliotecas do projeto. Não indicam classes Python com prefixo I nem novos serviços independentes.',left,y,pw-left-right)
        rows=[['Componente','Interface fornecida','Interface requerida','Finalidade técnica'],
            ['Interface web','Interface visual','INanaSmartREST','Operações, gráficos, autenticação e downloads.'],
            ['API NanaSmart','INanaSmartREST','IPersistenciaORM; IGeracaoConteudo por seu módulo de IA','Publicar /api/*, validar entradas e aplicar escopo por empresa.'],
            ['Identidade e acesso','IAutenticacao; IContas; IPoliticasAcesso','IPersistenciaORM','JWT (login/refresh), perfil, empresas, usuários e permissões.'],
            ['Gestão de ativos','IAtivos','IPersistenciaORM; IContas; IOrdemServico; IA opcional em signals','Equipamentos, planos e criticidade; gatilhos por horímetro.'],
            ['Monitoramento','ITelemetria; IAlertas','IAtivos; IOrdemServico; IPoliticasAcesso; IPersistenciaORM','Leituras, tendências, ocorrências e vínculo de ordens.'],
            ['Manutenção','IOrdemServico; IDashboard','IAtivos; IContas; IAlertas; ITelemetria; IPersistenciaORM; IA para análise','Ordens, prioridades ABC, históricos e indicadores.'],
            ['Exportação','IExportacao','IAtivos; IOrdemServico; IAlertas; ITelemetria; IPersistenciaORM','Consultar dados autorizados e produzir CSV, XLSX e PDF.'],
            ['Assistente de IA','IAssistente','IGeracaoConteudo; IPersistenciaORM; dados dos módulos operacionais','Construir contexto e prompts; chat e análises por perfil.'],
            ['Persistência','IPersistenciaORM','Conexão PostgreSQL','Representar ORM e driver compartilhados pelos apps.'],
            ['Google Gemini','IGeracaoConteudo','Credencial de API e acesso HTTPS','Gerar conteúdo por meio do SDK google-genai.'],
        ]
        header_style=ParagraphStyle('th',parent=SMALL,fontName='Nana-Bold',textColor=HexColor('#FFFFFF'))
        table=Table([[p(html.escape(cell),header_style if ri==0 else SMALL) for cell in row] for ri,row in enumerate(rows)],colWidths=[89,104,164,150],hAlign='LEFT')
        table.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),HexColor(BLUE)),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('GRID',(0,0),(-1,-1),.5,HexColor('#CBDAE8')),
            ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#F5F8FC'),HexColor('#FFFFFF')]),
        ]))
        _,th=table.wrap(507,1000)
        assert y-th>65, ('Tabela excedeu a página',y,th)
        table.drawOn(c,left,y-th); y-=th+18
        y=draw_paragraph(c,'No desenho, esferas e cavidades destacam quatro contratos centrais. As demais interfaces são detalhadas nesta tabela. As chamadas internas usam Python e o ORM; a comunicação entre navegador e backend usa HTTP/JSON.',left,y,pw-left-right,SMALL)
    else:
        y=heading(c,'Nós de hardware e ambientes de execução',left,y)
        y=draw_paragraph(c,'<b>Estação local:</b> o fluxo documentado usa um navegador, Python com Django e um serviço PostgreSQL em localhost. O navegador abre FrontATT/index.html; o backend é iniciado por <b>python manage.py runserver 127.0.0.1:9000</b>. O arquivo app/settings.py seleciona PostgreSQL em localhost:5432, banco manutencao.',left,y,pw-left-right)
        y=draw_paragraph(c,'<b>Processo auxiliar opcional:</b> scripts/simulador_realtime.py carrega o ambiente Django e grava leituras por modelos/ORM. Essas gravações executam os signals de telemetria. O comando manage.py analisar_tendencias pode executar a análise em lote; não há um agendador definido no repositório.',left,y,pw-left-right)
        y=draw_paragraph(c,'<b>Serviços externos:</b> o navegador carrega bibliotecas da CDN cdnjs.cloudflare.com. O backend acessa a API gerenciada Google Gemini quando há chave e recurso de IA acionado. A infraestrutura física desses fornecedores não é especificada pelo projeto.',left,y,pw-left-right)
        y=heading(c,'Protocolos de rede e comunicação',left,y-16)
        y=draw_paragraph(c,'<b>Navegador ↔ backend:</b> HTTP em TCP 9000, estilo REST, mensagens JSON e JWT Bearer nas rotas autenticadas. O frontend utiliza fetch e consulta periodicamente os dados exibidos.',left,y,pw-left-right)
        y=draw_paragraph(c,'<b>Python ↔ PostgreSQL:</b> protocolo PostgreSQL sobre TCP 5432, executando consultas SQL pelo Django ORM e psycopg2. O simulador acessa o banco por esse mesmo mecanismo, sem enviar leituras por HTTP.',left,y,pw-left-right)
        y=draw_paragraph(c,'<b>Acessos externos:</b> HTTPS em TCP 443 para carregar as bibliotecas JavaScript e para consumir Gemini por google-genai. Dentro do backend, módulos e signals se comunicam no processo Python.',left,y,pw-left-right)
        y=heading(c,'Artefatos de execução implantados',left,y-16)
        y=draw_paragraph(c,'<b>Navegador:</b> index.html, app.js, styles.css e live-chart.js de FrontATT/, além das bibliotecas CDN. <b>Python/Django:</b> manage.py, app/ e os apps accounts, authentication, ativos, manutencao, telemetria, alertas, exportacao e gemini_api, com dependências de requirements.txt. <b>CLI:</b> script de simulação e, quando executados, comandos de gerenciamento. <b>PostgreSQL:</b> tabelas, índices e relacionamentos mantidos pelas migrations.',left,y,pw-left-right)
        y=draw_paragraph(c,'<b>Escopo:</b> esta é a topologia local identificada no código e no README. O repositório não define uma topologia de produção nem integração de rede com sensores físicos; por isso, tais nós não são apresentados como implantados.',left,y,pw-left-right,SMALL)
    assert y>48, ('Conteúdo excedeu a página',number,y)
    c.setStrokeColor(HexColor(BORDER)); c.line(left,35,pw-right,35)
    c.setFont('Nana',8); c.setFillColor(HexColor(MUTED))
    c.drawString(left,23,'NanaSmart | Código e documentação do repositório | 11/11/2026')
    c.drawRightString(pw-right,23,f'Item {number} | 2/2')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    data=[('03_Diagrama_de_Pacotes',packages()),('04_Diagrama_de_Componentes',components()),('05_Diagrama_de_Implantacao',deployment())]
    for name,d in data:
        pdf=OUT/f'{name}.pdf'
        c=canvas.Canvas(str(pdf),pagesize=landscape(A3),pageCompression=1)
        c.setTitle(f'NanaSmart - {d.title}'); c.setAuthor('Equipe NanaSmart')
        c.setSubject(f'UML 2.5 - item {d.number} do template de modelagem arquitetural')
        d.draw_pdf(c); c.showPage(); details(c,d.number); c.showPage(); c.save()
        d.save_drawio(OUT/f'{name}.drawio')
        subprocess.run(['pdftoppm','-f','1','-l','1','-singlefile','-scale-to','3600','-png',str(pdf),str(OUT/name)],check=True,capture_output=True)
        print(pdf)


if __name__=='__main__':
    main()
