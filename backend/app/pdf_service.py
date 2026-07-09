"""
Génération de documents PDF — CodeRoute Guinée (DNTT).

Convocations et attestations produites avec ReportLab : accents corrects
(UTF-8), mise en page officielle, couleurs nationales guinéennes, QR code
de vérification. Le rendu « fait main » précédent (primitives PDF brutes)
cassait les accents et donnait une présentation rudimentaire.
"""
from __future__ import annotations

import io
from datetime import datetime

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# ── Couleurs nationales guinéennes ──────────────────────────────────────────
GUINEA_RED = colors.HexColor("#CE1126")
GUINEA_YELLOW = colors.HexColor("#FCD116")
GUINEA_GREEN = colors.HexColor("#009460")
INK = colors.HexColor("#0A2540")
MUTED = colors.HexColor("#5A6B7B")
LINE = colors.HexColor("#D9E1E8")
LIGHT_BG = colors.HexColor("#F4F7F9")

PAGE_W, PAGE_H = A4
MARGIN = 20 * mm


def _fmt_datetime(value: object) -> str:
    if not value:
        return "—"
    s = str(value)
    try:
        dt = datetime.fromisoformat(s.replace("Z", ""))
        return dt.strftime("%d/%m/%Y à %Hh%M")
    except (ValueError, TypeError):
        return s


def _fmt_date_only(value: object) -> str:
    if not value:
        return "—"
    s = str(value)
    try:
        dt = datetime.fromisoformat(s.replace("Z", ""))
        return dt.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return s


def _qr_image(payload: str) -> ImageReader:
    qr = qrcode.QRCode(border=1, box_size=10)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    b = io.BytesIO()
    img.save(b, format="PNG")
    b.seek(0)
    return ImageReader(b)


def _draw_flag_band(c: canvas.Canvas, y: float, height: float = 4 * mm) -> None:
    third = (PAGE_W - 2 * MARGIN) / 3
    for i, col in enumerate((GUINEA_RED, GUINEA_YELLOW, GUINEA_GREEN)):
        c.setFillColor(col)
        c.rect(MARGIN + i * third, y, third, height, stroke=0, fill=1)


def _header(c: canvas.Canvas, title: str, subtitle: str) -> float:
    top = PAGE_H - MARGIN
    _draw_flag_band(c, top - 4 * mm)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN, top - 14 * mm, "RÉPUBLIQUE DE GUINÉE")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, top - 18.5 * mm, "Travail — Justice — Solidarité")
    c.drawString(MARGIN, top - 22.5 * mm, "Direction Nationale des Transports Terrestres (DNTT)")
    c.setFillColor(GUINEA_GREEN)
    c.setFont("Helvetica-Bold", 15)
    c.drawRightString(PAGE_W - MARGIN, top - 14 * mm, "CodeRoute Guinée")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 8)
    c.drawRightString(PAGE_W - MARGIN, top - 18.5 * mm, "Plateforme nationale de l'examen du code")
    band_y = top - 34 * mm
    c.setFillColor(INK)
    c.rect(MARGIN, band_y, PAGE_W - 2 * MARGIN, 10 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(PAGE_W / 2, band_y + 3 * mm, title)
    if subtitle:
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 9)
        c.drawCentredString(PAGE_W / 2, band_y - 5 * mm, subtitle)
        return band_y - 12 * mm
    return band_y - 6 * mm


def _section(c: canvas.Canvas, y: float, number: str, label: str) -> float:
    c.setFillColor(GUINEA_GREEN)
    c.setFont("Helvetica-Bold", 10.5)
    c.drawString(MARGIN, y, f"{number}. {label.upper()}")
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(MARGIN, y - 2 * mm, PAGE_W - MARGIN, y - 2 * mm)
    return y - 8 * mm


def _row(c: canvas.Canvas, y: float, key: str, value: str, key_w: float = 48 * mm) -> float:
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9.5)
    c.drawString(MARGIN + 2 * mm, y, key)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(MARGIN + 2 * mm + key_w, y, str(value) if value else "—")
    return y - 6.2 * mm


def _footer(c: canvas.Canvas, reference: str) -> None:
    c.setStrokeColor(LINE)
    c.setLineWidth(0.6)
    c.line(MARGIN, MARGIN + 8 * mm, PAGE_W - MARGIN, MARGIN + 8 * mm)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7.5)
    c.drawString(MARGIN, MARGIN + 3.5 * mm,
                 "Document officiel généré par CodeRoute Guinée — vérifiable au centre agréé.")
    c.drawRightString(PAGE_W - MARGIN, MARGIN + 3.5 * mm, f"Réf. {reference}")


def build_convocation_pdf(convocation: dict) -> bytes:
    candidate = convocation["candidate"]
    session = convocation["session"]
    center = convocation["center"]

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Convocation {convocation['reference']}")

    y = _header(c, "CONVOCATION À L'EXAMEN DU CODE DE LA ROUTE",
                f"Référence : {convocation['reference']}  ·  Émise le {_fmt_date_only(convocation.get('issued_at'))}")

    qr = _qr_image(convocation["qr_payload"])
    qr_size = 32 * mm
    qr_x = PAGE_W - MARGIN - qr_size
    qr_y = y - qr_size - 2 * mm
    c.drawImage(qr, qr_x, qr_y, qr_size, qr_size)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 7)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 3.5 * mm, "Vérification au centre")

    y = _section(c, y, "1", "Identité du candidat")
    y = _row(c, y, "Référence candidat", candidate["reference"])
    y = _row(c, y, "Nom complet", candidate["full_name"])
    y = _row(c, y, "Pièce d'identité", candidate["identity_number"])
    y = _row(c, y, "Téléphone", candidate["phone"])
    y = _row(c, y, "Catégorie de permis", candidate["permit_category"])

    y -= 3 * mm
    y = _section(c, y, "2", "Session d'examen")
    y = _row(c, y, "Référence session", session["reference"])
    y = _row(c, y, "Date et heure", _fmt_datetime(session["starts_at"]))
    y = _row(c, y, "Centre agréé", center["name"])
    y = _row(c, y, "Code centre", center["code"])
    y = _row(c, y, "Ville", center["city"])
    y = _row(c, y, "Adresse", center["address"])

    y -= 3 * mm
    y = _section(c, y, "3", "Contrôle d'entrée")
    y = _row(c, y, "Code de vérification", convocation["verification_code"])
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Oblique", 8.5)
    c.drawString(MARGIN + 2 * mm, y,
                 "À présenter avec le QR code ci-dessus et une pièce d'identité originale.")
    y -= 8 * mm

    y = _section(c, y, "4", "Consignes au candidat")
    consignes = [
        "Se présenter 30 minutes avant l'heure de la session.",
        "Présenter une pièce d'identité officielle en cours de validité.",
        "Tout retard, substitution ou tentative de fraude entraîne un refus d'entrée.",
        "La convocation (QR code) est obligatoire pour accéder à la salle.",
    ]
    box_h = len(consignes) * 6 * mm + 4 * mm
    c.setFillColor(LIGHT_BG)
    c.rect(MARGIN, y - box_h + 3 * mm, PAGE_W - 2 * MARGIN, box_h, stroke=0, fill=1)
    ty = y - 2 * mm
    for item in consignes:
        c.setFillColor(GUINEA_GREEN)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(MARGIN + 3 * mm, ty, "•")
        c.setFillColor(INK)
        c.setFont("Helvetica", 9.5)
        c.drawString(MARGIN + 7 * mm, ty, item)
        ty -= 6 * mm

    _footer(c, convocation["reference"])
    c.showPage()
    c.save()
    return buf.getvalue()


def build_result_certificate_pdf(candidate: dict, session: dict, center: dict, attempt: dict) -> bytes:
    passed = bool(attempt.get("passed"))
    decision = "ADMIS(E)" if passed else "NON ADMIS(E)"
    decision_color = GUINEA_GREEN if passed else GUINEA_RED

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Attestation {candidate['reference']}")

    y = _header(c, "ATTESTATION DE RÉSULTAT — CODE DE LA ROUTE",
                f"Candidat : {candidate['reference']}")

    c.setFillColor(decision_color)
    c.rect(MARGIN, y - 12 * mm, PAGE_W - 2 * MARGIN, 12 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(PAGE_W / 2, y - 8.5 * mm, decision)
    y -= 20 * mm

    y = _section(c, y, "1", "Identité du candidat")
    y = _row(c, y, "Référence candidat", candidate["reference"])
    y = _row(c, y, "Nom complet", candidate["full_name"])
    y = _row(c, y, "Pièce d'identité", candidate["identity_number"])
    y = _row(c, y, "Catégorie de permis", candidate["permit_category"])

    y -= 3 * mm
    y = _section(c, y, "2", "Examen")
    y = _row(c, y, "Session", session["reference"])
    y = _row(c, y, "Date de l'examen", _fmt_datetime(session["starts_at"]))
    y = _row(c, y, "Centre", center["name"])
    y = _row(c, y, "Ville", center["city"])

    y -= 3 * mm
    y = _section(c, y, "3", "Résultat")
    score = attempt.get("score")
    y = _row(c, y, "Score obtenu", f"{score} / 40" if score is not None else "—")
    y = _row(c, y, "Décision", decision)
    y = _row(c, y, "Date de soumission", _fmt_datetime(attempt.get("submitted_at")))

    _footer(c, candidate["reference"])
    c.showPage()
    c.save()
    return buf.getvalue()


def _escape_pdf_text(value: object) -> str:
    text = str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text.encode("latin-1", "replace").decode("latin-1")


def build_simple_pdf(title: str, lines: list[str], qr_payload: str | None = None) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(title)
    y = _header(c, title[:60], "")
    c.setFillColor(INK)
    c.setFont("Helvetica", 10)
    for line in lines:
        if y < MARGIN + 20 * mm:
            _footer(c, "—")
            c.showPage()
            y = PAGE_H - MARGIN
        if not line:
            y -= 4 * mm
            continue
        if len(line) > 2 and line[0].isdigit() and line[1] == ".":
            c.setFillColor(GUINEA_GREEN)
            c.setFont("Helvetica-Bold", 10.5)
            c.drawString(MARGIN, y, line)
            c.setFillColor(INK)
            c.setFont("Helvetica", 10)
        else:
            c.drawString(MARGIN, y, line)
        y -= 6 * mm
    _footer(c, "—")
    c.showPage()
    c.save()
    return buf.getvalue()


def _format_status_counts(label: str, values: dict[str, int]) -> list[str]:
    if not values:
        return [f"{label}: aucune donnee consolidee"]
    return [f"{label} - {status}: {count}" for status, count in sorted(values.items())]


def _status_table(c: canvas.Canvas, y: float, label: str, values: dict) -> float:
    """Petit tableau de statuts (clé : nombre). Retourne le y sous le bloc."""
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(MARGIN + 2 * mm, y, label)
    y -= 5.5 * mm
    if not values:
        c.setFillColor(MUTED)
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(MARGIN + 6 * mm, y, "Aucune donnée consolidée")
        return y - 6 * mm
    for status_name, count in sorted(values.items()):
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 9)
        c.drawString(MARGIN + 6 * mm, y, str(status_name))
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(MARGIN + 70 * mm, y, str(count))
        y -= 5 * mm
    return y - 2 * mm


def build_institutional_report_pdf(report: dict) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("Rapport institutionnel — CodeRoute Guinée")

    y = _header(c, "RAPPORT INSTITUTIONNEL — DISPOSITIF NATIONAL",
                report.get("generated_for", "État guinéen"))

    # ── Score de maturité (jauge visuelle) ──
    score = int(report.get("readiness_score", 0))
    label = report.get("readiness_label", "—")
    score_color = GUINEA_GREEN if score >= 75 else (GUINEA_YELLOW if score >= 50 else GUINEA_RED)

    c.setFillColor(LIGHT_BG)
    c.rect(MARGIN, y - 20 * mm, PAGE_W - 2 * MARGIN, 20 * mm, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(MARGIN + 4 * mm, y - 7 * mm, "Score de maturité du dispositif")
    c.setFillColor(score_color)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(MARGIN + 4 * mm, y - 16 * mm, f"{score}%")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 10)
    c.drawString(MARGIN + 32 * mm, y - 16 * mm, str(label))
    # Barre de progression
    bar_x = MARGIN + 90 * mm
    bar_w = PAGE_W - MARGIN - bar_x - 4 * mm
    c.setFillColor(colors.HexColor("#E3E9EE"))
    c.rect(bar_x, y - 13 * mm, bar_w, 5 * mm, stroke=0, fill=1)
    c.setFillColor(score_color)
    c.rect(bar_x, y - 13 * mm, bar_w * min(score, 100) / 100, 5 * mm, stroke=0, fill=1)
    y -= 26 * mm

    # ── Indicateurs clés ──
    y = _section(c, y, "1", "Indicateurs clés")
    y = _row(c, y, "Candidats référencés", str(report.get("candidates", 0)))
    y = _row(c, y, "Événements d'audit", str(report.get("audit_events", 0)))
    y -= 2 * mm

    # ── Répartitions par statut (2 colonnes) ──
    y = _section(c, y, "2", "Répartitions consolidées")
    y_start = y
    y = _status_table(c, y, "Centres", report.get("centers_by_status", {}))
    y = _status_table(c, y, "Questions", report.get("questions_by_status", {}))
    # Colonne droite
    y_right = y_start
    c.setFillColor(INK)
    for label2, values2 in (("Contrôles d'identité", report.get("identity_checks_by_status", {})),
                            ("Habilitations", report.get("authorizations_by_status", {}))):
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(PAGE_W / 2 + 4 * mm, y_right, label2)
        y_right -= 5.5 * mm
        vals = values2 or {}
        if not vals:
            c.setFillColor(MUTED); c.setFont("Helvetica-Oblique", 9)
            c.drawString(PAGE_W / 2 + 8 * mm, y_right, "Aucune donnée")
            y_right -= 6 * mm
        for sname, cnt in sorted(vals.items()):
            c.setFillColor(MUTED); c.setFont("Helvetica", 9)
            c.drawString(PAGE_W / 2 + 8 * mm, y_right, str(sname))
            c.setFillColor(INK); c.setFont("Helvetica-Bold", 9)
            c.drawRightString(PAGE_W - MARGIN - 4 * mm, y_right, str(cnt))
            y_right -= 5 * mm
        y_right -= 2 * mm
    y = min(y, y_right) - 2 * mm

    # ── Recommandations ──
    y = _section(c, y, "3", "Recommandations prioritaires")
    recommendations = report.get("recommendations") or []
    c.setFont("Helvetica", 9.5)
    for i, rec in enumerate(recommendations[:8], start=1):
        if y < MARGIN + 25 * mm:
            _footer(c, "Rapport institutionnel")
            c.showPage()
            y = PAGE_H - MARGIN
        c.setFillColor(GUINEA_GREEN)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(MARGIN + 2 * mm, y, f"{i}.")
        c.setFillColor(INK)
        c.setFont("Helvetica", 9.5)
        # Découpe le texte long sur plusieurs lignes
        text = str(rec)
        max_chars = 95
        while text:
            chunk = text[:max_chars]
            if len(text) > max_chars:
                cut = chunk.rfind(" ")
                if cut > 40:
                    chunk = chunk[:cut]
            c.drawString(MARGIN + 8 * mm, y, chunk)
            text = text[len(chunk):].lstrip()
            y -= 5.5 * mm

    _footer(c, "Rapport institutionnel")
    c.showPage()
    c.save()
    return buf.getvalue()
