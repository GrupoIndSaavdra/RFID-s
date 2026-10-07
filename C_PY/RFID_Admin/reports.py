from logger import log_error
import os
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def generar_reporte_pdf(ruta, area, logs, perm, den) -> bool:
    try:
        plt.figure(figsize=(6, 4))
        if sum(v := [perm, den]) == 0:
            plt.pie(
                [1],
                labels=["Sin registros"],
                colors=["#D3D3D3"],
                wedgeprops=dict(width=0.4, edgecolor="w"),
            )
        else:
            plt.pie(
                v,
                labels=[f"{c} ({x})" for c, x in zip(["Permitidos", "Denegados"], v)],
                colors=["#0A8504", "#9C0303"],
                autopct="%1.1f%%",
                startangle=90,
                wedgeprops=dict(width=0.4, edgecolor="w"),
                textprops={"fontsize": 10, "fontweight": "bold"},
            )

        plt.title(f"Resumen de Accesos: {area}", fontsize=14)
        tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_chart.png")
        plt.tight_layout()
        plt.savefig(tmp)
        plt.close()

        doc = SimpleDocTemplate(
            ruta,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30,
        )
        est = getSampleStyleSheet()
        elems = [
            Paragraph(
                f"Reporte de Accesos - {area}",
                ParagraphStyle(
                    "Titulo", parent=est["Heading1"], alignment=1, spaceAfter=20
                ),
            ),
            RLImage(tmp, width=400, height=266),
            Spacer(1, 20),
        ]

        if logs:
            t = Table(
                [["UID", "Nombre", "Área", "Fecha", "Motivo", "Entrada", "Salida"]]
                + [list(l) for l in logs],
                colWidths=[50, 110, 85, 60, 125, 50, 50],
            )
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2B2D30")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F6F9")),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            elems.append(t)
        else:
            elems.append(
                Paragraph("No hay registros en la vista actual.", est["Normal"])
            )

        doc.build(elems)
        if os.path.exists(tmp):
            os.remove(tmp)
        return True
    except Exception as e:
        log_error(f"Error generando PDF: {e}")
        return False
