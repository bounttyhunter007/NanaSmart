"""Exporta imagens compactas e os campos separados dos itens 3, 4 e 5."""
from pathlib import Path
import importlib.util
import html
import subprocess
import tempfile

from PIL import Image, ImageChops
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, A3

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('diagramas', HERE / 'gerar_diagramas.py')
uml = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uml)
uml.W = uml.H = 1000
OUT = HERE.parent / 'Para_preencher_template'
OUT.mkdir(exist_ok=True)


def base(n):
    d = uml.Diagram(n, '', '')
    d.ops = []
    return d


def pacotes():
    d=base(3)
    d.package(30,40,280,130,'FrontATT','Interface Vue 3\nCliente da API REST',fontsize=18)
    d.package(360,40,280,130,'app','Configurações Django\nRoteamento /api/*',fontsize=18)
    d.package(690,40,280,130,'scripts','Carga e simulação\nUsa modelos Django',fontsize=18)
    d.package(30,310,280,415,'Acesso','Agrupamento lógico',uml.PALE,18)
    d.package(50,395,240,110,'authentication','Login e perfil',fontsize=18)
    d.package(50,565,240,140,'accounts','Empresas, usuários\ne permissões',fontsize=18)
    d.package(360,310,280,595,'Operação','Agrupamento lógico',uml.PALE,18)
    d.package(380,395,240,105,'ativos','Equipamentos e planos',fontsize=17)
    d.package(380,555,240,125,'manutencao','Ordens e históricos\nSubpacote: dashboards',fontsize=16)
    d.package(380,735,240,80,'telemetria','Sensores e tendências',fontsize=17)
    d.package(380,840,240,48,'alertas',fontsize=18)
    d.package(690,310,280,415,'Integrações e saídas','Agrupamento lógico',uml.PALE,18)
    d.package(710,395,240,130,'gemini_api','Contexto e prompts\nIntegração Gemini',uml.LILAC,18)
    d.package(710,585,240,120,'exportacao','Relatórios CSV,\nExcel e PDF',uml.GREEN,18)
    d.line([(310,105),(360,105)],dash=True,arrow=True)
    d.line([(450,170),(450,245),(170,245),(170,333)],dash=True,arrow=True)
    d.line([(500,170),(500,333)],dash=True,arrow=True)
    d.label(590,200,'rotas',17)
    d.line([(550,170),(550,245),(830,245),(830,310)],dash=True,arrow=True)
    d.line([(170,505),(170,588)],dash=True,arrow=True)
    d.line([(470,555),(470,500)],dash=True,arrow=True)
    d.line([(535,500),(535,578)],dash=True,arrow=True)
    d.line([(500,815),(500,863)],dash=True,arrow=True)
    d.line([(360,635),(310,635)],dash=True,arrow=True)
    d.line([(690,460),(640,460)],dash=True,arrow=True)
    d.line([(640,625),(690,625)],dash=True,arrow=True)
    d.text(35,946,'Seta tracejada: dependência do cliente para o fornecedor.',18,uml.MUTED)
    return d


def componentes():
    d=base(4)
    d.component(50,35,360,155,'Interface web','FrontATT / Vue 3\nTelas e cliente HTTP com JWT')
    d.component(50,385,500,400,'API NanaSmart','Django REST Framework\n\naccounts + authentication\nativos + manutencao / dashboards\ntelemetria + alertas\ngemini_api + exportacao\n\nServiços, políticas e signals',uml.PALE)
    d.component(700,385,270,185,'Persistência','Django ORM\nDriver psycopg2\nBanco PostgreSQL')
    d.component(700,680,270,145,'Google Gemini','Serviço externo\nGeração de conteúdo',uml.LILAC)
    # Contrato REST: interface fornecida pela API e requerida pela interface web.
    d.line([(230,190),(230,273)],uml.BLUE,2)
    d.line([(230,295),(230,385)],uml.BLUE,2)
    d.circle(230,287,8)
    from math import pi,cos,sin
    d.line([(230+14*cos(pi+i*pi/32),287+14*sin(pi+i*pi/32)) for i in range(33)],uml.BLUE,2)
    d.label(390,264,'INanaSmartREST',18)
    d.label(390,294,'HTTP / JSON + JWT',16)
    d.assembly((550,475),(700,475),'IPersistenciaORM',label_y=430)
    d.assembly((550,750),(700,750),'IGeracaoConteudo',label_y=700)
    d.text(50,882,'Esfera: interface fornecida. Cavidade: interface requerida.',18,uml.MUTED)
    d.text(50,916,'As interfaces representam contratos conceituais do sistema.',18,uml.MUTED)
    return d


def implantacao():
    d=base(5)
    d.node(30,40,650,800,'device','Máquina de desenvolvimento',uml.PALE)
    d.node(60,160,250,230,'executionEnvironment','Navegador web')
    d.artifact(75,240,220,125,'FrontATT/','index.html e app.js\nstyles.css e live-chart.js')
    d.node(365,160,285,320,'executionEnvironment','Python / Django')
    d.text(382,228,'127.0.0.1:9000',18,uml.MUTED)
    d.artifact(381,285,253,160,'Backend NanaSmart','app/ e apps Django\nmanage.py\nrequirements.txt\nChave Gemini opcional')
    d.node(60,640,250,160,'executionEnvironment','Python CLI opcional')
    d.artifact(75,712,220,68,'simulador_realtime.py')
    d.node(365,640,285,160,'executionEnvironment','PostgreSQL')
    d.artifact(381,712,253,68,'Banco manutencao')
    d.node(760,40,210,220,'node','CDN externa',uml.GREEN)
    d.text(775,112,'cdnjs.cloudflare.com\n\nVue 3 e bibliotecas\nJavaScript via CDN',16)
    d.node(760,640,210,160,'node','Google Gemini',uml.LILAC)
    d.text(775,714,'API gerenciada\nGeração de conteúdo',16)
    d.line([(310,330),(365,330)],uml.BLUE,2)
    d.label(337,265,'HTTP\n9000',16)
    d.line([(507,480),(507,640)],uml.BLUE,2)
    d.label(507,525,'SQL / TCP 5432\nDjango ORM / psycopg2',17)
    d.line([(310,750),(365,750)],uml.BLUE,2)
    d.label(337,688,'SQL\n5432',16)
    d.line([(185,160),(185,132),(720,132),(720,150),(760,150)],uml.BLUE,2)
    d.label(540,104,'HTTPS / TCP 443',17)
    d.line([(650,380),(720,380),(720,730),(760,730)],uml.BLUE,2)
    d.label(770,492,'HTTPS\nTCP 443',17)
    d.text(35,885,'Linhas contínuas: caminhos de comunicação entre ambientes.',18,uml.MUTED)
    d.text(35,919,'Cenário local. O simulador opcional grava pelos modelos Django.',18,uml.MUTED)
    return d


MEMORIA = (
    'O NanaSmart organiza a interface Vue 3 no pacote FrontATT e o backend Django em apps de negócio. '
    'O pacote app centraliza a configuração e as rotas REST. '
    'O agrupamento Acesso reúne authentication e accounts, responsáveis por identidade, empresas e permissões. '
    'Operação reúne ativos, manutencao, telemetria e alertas; dashboards é um subpacote de manutencao. '
    'Integrações e saídas reúne gemini_api e exportacao, que utilizam dados operacionais. '
    'scripts apoia a carga e a simulação de dados. '
    'Serviços, serializers e o adapter Gemini delimitam responsabilidades e contratos. '
    'Há acoplamento entre apps, inclusive dependências recíprocas entre ativos e manutencao. '
    'Os módulos Python são públicos; autenticação, perfis e filtros por empresa controlam o acesso pela API. '
    'Os agrupamentos lógicos do desenho não representam novos diretórios.'
)

HEADERS = ['Componente','Interface Fornecida (Provided)','Interface Requerida (Required)','Finalidade Técnica / Descrição']
ROWS = [
    ['Interface web','Interface visual','INanaSmartREST','Apresentar as telas Vue 3 e consumir a API com JWT.'],
    ['API NanaSmart','INanaSmartREST','IPersistenciaORM; IGeracaoConteudo','Oferecer autenticação, ativos, manutenção, telemetria, alertas, dashboards, exportação e IA; aplicar permissões e escopo por empresa.'],
    ['Persistência','IPersistenciaORM','Conexão PostgreSQL','Executar consultas e gravações pelo Django ORM e pelo driver psycopg2.'],
    ['Google Gemini','IGeracaoConteudo','Credencial de API e acesso HTTPS','Gerar conteúdo de IA solicitado pelo backend por meio do SDK google-genai.'],
]

INFRA = [
    ('Nós de Hardware e Ambientes de Execução',
     'O cenário local utiliza uma máquina de desenvolvimento com navegador web, Python com Django e PostgreSQL. '
     'O navegador abre FrontATT/index.html e o backend executa em 127.0.0.1:9000. '
     'Um processo Python CLI opcional executa o simulador de telemetria. '
     'Os nós externos são a CDN cdnjs.cloudflare.com e o serviço Google Gemini, acessado quando a integração de IA está configurada.'),
    ('Protocolos de Rede e Comunicação',
     'O navegador consome a API por HTTP/REST em TCP 9000, com mensagens JSON e autenticação JWT Bearer. '
     'Django e o simulador acessam PostgreSQL em localhost:5432 por seu protocolo TCP, executando SQL pelo ORM e psycopg2. '
     'A CDN e a API Gemini utilizam HTTPS em TCP 443. '
     'Os módulos de negócio e os signals se comunicam dentro do processo Python.'),
    ('Artefatos de Execução Implantados',
     'No navegador são carregados index.html, app.js, styles.css e live-chart.js de FrontATT/, além das bibliotecas da CDN. '
     'No ambiente Django ficam manage.py, app/ e os apps accounts, authentication, ativos, manutencao, telemetria, alertas, exportacao e gemini_api, com as dependências de requirements.txt. '
     'O processo CLI executa scripts/simulador_realtime.py. '
     'O PostgreSQL mantém o banco manutencao, com tabelas e índices criados pelas migrations.'),
]


def image(name,d):
    with tempfile.TemporaryDirectory(prefix='nana-template-') as temp:
        pdf=Path(temp)/'modelo.pdf'
        c=canvas.Canvas(str(pdf),pagesize=landscape(A3))
        d.draw_pdf(c); c.showPage(); c.save()
        prefix=Path(temp)/'modelo'
        subprocess.run(['pdftoppm','-singlefile','-scale-to','5000','-png',str(pdf),str(prefix)],check=True,capture_output=True)
        im=Image.open(prefix.with_suffix('.png')).convert('RGB')
        box=ImageChops.difference(im,Image.new('RGB',im.size,'white')).getbbox()
        pad=24
        box=(max(0,box[0]-pad),max(0,box[1]-pad),min(im.width,box[2]+pad),min(im.height,box[3]+pad))
        im.crop(box).save(OUT/name,dpi=(300,300))


def main():
    images=[('3_1_Diagrama_de_Pacotes.png',pacotes()),('4_1_Diagrama_de_Componentes.png',componentes()),('5_1_Diagrama_de_Implantacao.png',implantacao())]
    for name,d in images: image(name,d)
    (OUT/'3_2_Memoria_Descritiva.txt').write_text(MEMORIA+'\n',encoding='utf-8-sig')
    tab='\n'.join('\t'.join(row) for row in [HEADERS]+ROWS)+'\n'
    (OUT/'4_2_Mapeamento_de_Interfaces.txt').write_text(tab,encoding='utf-8-sig')
    infra='\n\n'.join(f'{title}:\n{body}' for title,body in INFRA)+'\n'
    (OUT/'5_2_Especificacao_da_Infraestrutura.txt').write_text(infra,encoding='utf-8-sig')
    table='<table><thead><tr>'+''.join(f'<th>{html.escape(v)}</th>' for v in HEADERS)+'</tr></thead><tbody>'
    table+=''.join('<tr>'+''.join(f'<td>{html.escape(v)}</td>' for v in row)+'</tr>' for row in ROWS)+'</tbody></table>'
    body=f'''<section id="item3"><h1>3. Diagrama de Pacotes UML</h1><h2>3.1. Modelo</h2>
<img src="3_1_Diagrama_de_Pacotes.png" alt="Diagrama de pacotes do NanaSmart">
<h2>3.2. Memória Descritiva</h2><p class="memoria">{MEMORIA}</p></section>
<section id="item4"><h1>4. Diagrama de Componentes UML</h1><h2>4.1. Modelo</h2>
<img src="4_1_Diagrama_de_Componentes.png" alt="Diagrama de componentes do NanaSmart">
<h2>4.2. Mapeamento de Interfaces do Sistema</h2>{table}</section>
<section id="item5"><h1>5. Diagrama de Implantação</h1><h2>5.1. Modelo</h2>
<img src="5_1_Diagrama_de_Implantacao.png" alt="Diagrama de implantação local do NanaSmart">
<h2>5.2. Especificação da Infraestrutura de Execução</h2><ul>'''
    body+=''.join(f'<li><strong>{title}:</strong> {text}</li>' for title,text in INFRA)+'</ul></section>'
    doc='''<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8"><title>NanaSmart itens 3 4 e 5</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#e8ebef;font-family:Arial,sans-serif;color:#111;font-size:12pt;line-height:1.3}
section{width:210mm;margin:20px auto;background:white;padding:22mm 25mm 24mm}
h1{font-size:18pt;color:#2d6db3;margin:0 0 16pt;font-weight:700}h2{font-size:14pt;color:#293548;margin:16pt 0 12pt}
p{margin:0 0 10pt;text-align:justify}img{display:block;width:100%;height:auto;margin:0 auto 12pt}
table{border-collapse:collapse;width:100%;font-size:10pt;line-height:1.22;table-layout:fixed}th,td{border:1px solid #c6d4e4;padding:9px;vertical-align:top;overflow-wrap:anywhere;text-align:left}
th{background:#2d6db3;color:#fff;font-weight:normal}tbody tr:nth-child(even){background:#f5f8fb}
li{margin-bottom:10pt}ul{padding-left:20px}.memoria{font-size:12pt;line-height:1.25}
@media print{body{background:white}section{margin:0;padding:0;width:auto;break-after:page}section:last-child{break-after:auto}h1,h2{break-after:avoid}img,tr,li{break-inside:avoid}@page{size:A4;margin:22mm 25mm 24mm}}
</style></head><body>'''+body+'</body></html>'
    (OUT/'Conteudo_para_copiar.html').write_text(doc,encoding='utf-8')
    (OUT/'COMO_PREENCHER.txt').write_text('''ARQUIVOS PARA PREENCHER O MODELO ANEXADO

3.1. Modelo: inserir 3_1_Diagrama_de_Pacotes.png.
3.2. Memória Descritiva: copiar o texto de 3_2_Memoria_Descritiva.txt.
O texto foi resumido para caber no limite de 15 linhas em Arial 12,
largura de 16 cm; a quantidade final de linhas depende da formatação do seu arquivo.

4.1. Modelo: inserir 4_1_Diagrama_de_Componentes.png.
4.2. Mapeamento de Interfaces do Sistema: copiar a tabela formatada
do arquivo Conteudo_para_copiar.html, aberto no navegador.
As quatro colunas são exatamente as pedidas no anexo.
O arquivo 4_2_Mapeamento_de_Interfaces.txt também contém os dados,
separados por tabulação, para colar nas células ou converter em tabela no Word.

5.1. Modelo: inserir 5_1_Diagrama_de_Implantacao.png.
5.2. Especificação da Infraestrutura de Execução: copiar os três tópicos
de 5_2_Especificacao_da_Infraestrutura.txt.

Abra Conteudo_para_copiar.html para ver os itens na sequência do modelo,
com as imagens, as descrições e a tabela prontas para seleção e cópia.
As imagens não contêm cabeçalho, rodapé ou numeração de página.
Os diagramas continuam representando a arquitetura geral do NanaSmart.
Os nomes de interfaces iniciados por I são contratos conceituais, não classes Python.
A implantação representa o ambiente local documentado no projeto.
''',encoding='utf-8-sig')
    print(OUT)


if __name__=='__main__': main()
