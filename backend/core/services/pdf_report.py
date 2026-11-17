from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from .portfolios import portfolio_summary


def portfolio_pdf(portfolio):
    output = BytesIO()
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output, title='Reporte de portafolio DataPulse Latam')
    summary = portfolio_summary(portfolio)
    story = [Paragraph('DataPulse Latam', styles['Title']),
        Paragraph(escape(portfolio.nombre), styles['Heading1']),
        Paragraph(escape(portfolio.descripcion or 'Sin descripción'), styles['BodyText']), Spacer(1, 12),
        Paragraph(f'Total activo USD: {summary["total_invertido_usd"]}', styles['BodyText']),
        Paragraph(f'IRPC ponderado: {summary["riesgo_promedio_ponderado"] or "Sin datos"}', styles['BodyText']),
        Paragraph('Un score más alto indica menor riesgo. Los cálculos parciales se indican en el detalle.', styles['BodyText']),
        Spacer(1, 12)]
    rows = [['País', 'Tipo', 'Monto USD', 'Entrada', 'Salida']]
    for position in portfolio.posiciones.all():
        rows.append([position.pais_id, position.tipo_activo, str(position.monto_inversion_usd),
                     str(position.fecha_entrada), str(position.fecha_salida or 'Activa')])
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#173b58')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white), ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10), ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)]))
    story.append(table)
    if summary['paises_con_datos_faltantes']:
        story.append(Paragraph('Datos de riesgo incompletos: ' + ', '.join(summary['paises_con_datos_faltantes']), styles['BodyText']))
    doc.build(story)
    return output.getvalue()
