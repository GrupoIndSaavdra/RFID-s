import os
import matplotlib # type: ignore
matplotlib.use('Agg')
import matplotlib.pyplot as plt # type: ignore
from reportlab.lib.pagesizes import A4 # type: ignore
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle # type: ignore
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle # type: ignore
from reportlab.lib import colors # type: ignore

def generar_reporte_pdf(ruta_archivo, area_filtrar, logs_datos, permitidos, denegados):
    """
    Genera un reporte PDF con una gráfica de barras y la tabla de registros.
    """
    try:
        # 1. Generar la gráfica de pastel circular (donut)
        plt.figure(figsize=(6, 4))
        categorias = ['Permitidos', 'Denegados']
        valores = [permitidos, denegados]
        colores = ['#0A8504', '#9C0303']
        
        if sum(valores) == 0:
            plt.pie([1], labels=["Sin registros"], colors=['#D3D3D3'], wedgeprops=dict(width=0.4, edgecolor='w'))
        else:
            # autopct permite mostrar el porcentaje, startangle rota el inicio y wedgeprops hace el hueco (donut)
            plt.pie(valores, labels=[f"{c} ({v})" for c, v in zip(categorias, valores)], colors=colores, autopct='%1.1f%%',
                    startangle=90, wedgeprops=dict(width=0.4, edgecolor='w'),
                    textprops={'fontsize': 10, 'fontweight': 'bold'})
            
        plt.title(f'Resumen de Accesos: {area_filtrar}', fontsize=14)
            
        temp_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_chart.png")
        plt.tight_layout()
        plt.savefig(temp_img_path)
        plt.close()
        
        # 2. Crear documento PDF
        doc = SimpleDocTemplate(ruta_archivo, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elementos = []
        estilos = getSampleStyleSheet()
        
        # Título
        estilo_titulo = ParagraphStyle('Titulo', parent=estilos['Heading1'], alignment=1, spaceAfter=20)
        elementos.append(Paragraph(f"Reporte de Accesos - {area_filtrar}", estilo_titulo))
        
        # Gráfica
        elementos.append(RLImage(temp_img_path, width=400, height=266))
        elementos.append(Spacer(1, 20))
        
        # Tabla
        if logs_datos:
            datos_tabla = [["UID", "Nombre", "Área", "Fecha", "Motivo", "Entrada", "Salida"]]
            for log in logs_datos:
                datos_tabla.append(list(log))
                
            t = Table(datos_tabla, colWidths=[50, 110, 85, 60, 125, 50, 50])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2B2D30")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 12),
                ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#F4F6F9")),
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('FONTSIZE', (0,0), (-1,-1), 8),
            ]))
            elementos.append(t)
        else:
            elementos.append(Paragraph("No hay registros en la vista actual.", estilos['Normal']))
            
        # Construir PDF
        doc.build(elementos)
        
        # Borrar imagen temporal
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)
            
        return True
    except Exception as e:
        print(f"Error generando PDF: {e}")
        return False
