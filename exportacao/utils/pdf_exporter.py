"""
Utilitário para exportação de dados em formato PDF.
Utiliza reportlab para geração nativa de PDFs com tabelas profissionais.
"""
from io import BytesIO
from xml.sax.saxutils import escape
from django.http import HttpResponse
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from .base_exporter import Exportador

class ExportadorPDF(Exportador):
    def __init__(self, orientacao='landscape'):
        self._orientacao = orientacao

    def exportar(self, nome: str, titulo: str, colunas: list, linhas: list) -> HttpResponse:
        """
        Gera um HttpResponse com conteúdo PDF pronto para download.
        """
        buffer = BytesIO()
        page_size = landscape(A4) if self._orientacao == 'landscape' else A4

        doc = SimpleDocTemplate(
            buffer,
            pagesize=page_size,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=20 * mm,
            bottomMargin=15 * mm,
        )

        elements = []
        styles = getSampleStyleSheet()

        # ── Estilos customizados ─────────────────────────────────────────
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=16,
            textColor=colors.HexColor('#2E4057'),
            spaceAfter=6,
            alignment=TA_CENTER,
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#888888'),
            alignment=TA_CENTER,
            spaceAfter=12,
        )
        cell_style = ParagraphStyle(
            'CellStyle',
            parent=styles['Normal'],
            fontSize=7,
            leading=9,
            alignment=TA_LEFT,
        )

        # ── Cabeçalho do relatório ───────────────────────────────────────
        elements.append(Paragraph(escape(f'NanaSmart — {titulo}'), title_style))
        data_geracao = timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')
        elements.append(Paragraph(f'Gerado em: {data_geracao}', subtitle_style))
        elements.append(Spacer(1, 6 * mm))

        # ── Prepara dados da tabela ──────────────────────────────────────
        # Envolve cada célula em Paragraph para suportar quebra de linha
        header_row = [Paragraph(escape(str(c)), ParagraphStyle(
            'HeaderCell', parent=cell_style, textColor=colors.white, fontName='Helvetica-Bold', fontSize=7
        )) for c in colunas]

        data_rows = []
        for linha in linhas:
            row = [Paragraph(escape(str(v)) if v is not None else '—', cell_style) for v in linha]
            data_rows.append(row)

        table_data = [header_row] + data_rows

        # ── Calcula larguras proporcionais ───────────────────────────────
        available_width = page_size[0] - 30 * mm  # margem esquerda + direita
        num_cols = len(colunas)
        col_width = available_width / num_cols if num_cols > 0 else available_width
        col_widths = [col_width] * num_cols

        # ── Cria tabela ──────────────────────────────────────────────────
        table = Table(table_data, colWidths=col_widths, repeatRows=1, splitInRow=1)

        # ── Estilização da tabela ────────────────────────────────────────
        style_commands = [
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4057')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 6),

            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 1), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ]

        # Zebra striping nas linhas de dados
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style_commands.append(
                    ('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F2F6FA'))
                )

        table.setStyle(TableStyle(style_commands))
        elements.append(table)

        # ── Rodapé com total de registros ────────────────────────────────
        elements.append(Spacer(1, 6 * mm))
        footer_style = ParagraphStyle(
            'Footer', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#999999')
        )
        elements.append(Paragraph(f'Total de registros: {len(linhas)}', footer_style))

        # ── Build PDF ────────────────────────────────────────────────────
        doc.build(elements)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{nome}.pdf"'
        return response
