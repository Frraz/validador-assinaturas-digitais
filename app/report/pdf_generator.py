from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from datetime import datetime
import os

def generate_report(validation_results, output_file):
    """
    Gera um relatório PDF com os resultados da validação
    
    Args:
        validation_results: Lista com resultados de validação
        output_file: Caminho do arquivo PDF a ser gerado
    """
    doc = SimpleDocTemplate(
        output_file,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Estilos para o documento
    styles = getSampleStyleSheet()
    
    # Em vez de adicionar estilos que já existem, criamos novos com nomes diferentes
    # ou modificamos os existentes
    title_style = ParagraphStyle(
        name='ReportTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=1,  # Centralizado
    )
    
    subtitle_style = ParagraphStyle(
        name='ReportSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
    )
    
    normal_style = styles['Normal']
    
    table_header_style = ParagraphStyle(
        name='TableHeader',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        alignment=1,
    )
    
    # Conteúdo do documento
    elements = []
    
    # Título e informações do relatório
    elements.append(Paragraph("Relatório de Validação de Assinaturas Digitais", title_style))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", normal_style))
    elements.append(Paragraph(f"Total de documentos analisados: {len(validation_results)}", normal_style))
    
    # Resumo
    valid_count = sum(1 for file in validation_results if file.get('status') == 'validado' and file.get('is_valid', False))
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Resumo da Validação", subtitle_style))
    
    summary_data = [
        ["Total de Documentos", str(len(validation_results))],
        ["Documentos com Assinatura Válida", str(valid_count)],
        ["Documentos com Assinatura Inválida", str(len(validation_results) - valid_count)]
    ]
    
    summary_table = Table(summary_data, colWidths=[10*cm, 5*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 1*cm))
    
    # Detalhes de cada documento
    elements.append(Paragraph("Detalhes da Validação por Documento", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))
    
    for idx, file_info in enumerate(validation_results, 1):
        filename = file_info.get('filename', f"Documento {idx}")
        status = file_info.get('status', 'desconhecido')
        
        elements.append(Paragraph(f"Documento {idx}: {filename}", normal_style))
        
        if status == 'erro':
            elements.append(Paragraph(f"Status: Erro na validação - {file_info.get('error', 'Erro desconhecido')}", normal_style))
        elif status == 'validado':
            is_valid = file_info.get('is_valid', False)
            validation_status = "Assinatura Válida" if is_valid else "Assinatura Inválida"
            elements.append(Paragraph(f"Status: {validation_status}", normal_style))
            
            # Se tiver detalhes disponíveis, exibi-los
            if 'details' in file_info:
                details = file_info['details']
                
                # Informações sobre assinaturas
                if 'valid_signatures' in details:
                    elements.append(Paragraph("Assinaturas Válidas:", normal_style))
                    for sig in details['valid_signatures']:
                        elements.append(Paragraph(f"• Assinante: {sig['signer']}", normal_style))
                        elements.append(Paragraph(f"  Data/Hora: {sig['signing_time']}", normal_style))
                        if sig.get('reason'):
                            elements.append(Paragraph(f"  Motivo: {sig['reason']}", normal_style))
                        if sig.get('location'):
                            elements.append(Paragraph(f"  Local: {sig['location']}", normal_style))
                
                if 'invalid_signatures' in details and details['invalid_signatures']:
                    elements.append(Paragraph("Assinaturas Inválidas:", normal_style))
                    for sig in details['invalid_signatures']:
                        elements.append(Paragraph(f"• Assinante: {sig['signer']}", normal_style))
                        elements.append(Paragraph(f"  Data/Hora: {sig['signing_time']}", normal_style))
                        if 'details' in sig and 'error_reasons' in sig['details']:
                            reasons = ", ".join(sig['details']['error_reasons'])
                            elements.append(Paragraph(f"  Problemas: {reasons}", normal_style))
                
                if 'error' in details:
                    elements.append(Paragraph(f"Erro: {details['error']}", normal_style))
        
        elements.append(Spacer(1, 0.5*cm))
    
    # Gerar documento PDF
    doc.build(elements)
    
    return output_file