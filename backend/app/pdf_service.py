import qrcode


def _escape_pdf_text(value: object) -> str:
    text = str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text.encode("latin-1", "replace").decode("latin-1")


def _qr_pdf_commands(payload: str, x: float = 418, y: float = 604, size: float = 118) -> list[str]:
    qr = qrcode.QRCode(border=1)
    qr.add_data(payload)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    cell = size / len(matrix)
    commands = ["0 0 0 rg"]
    for row_index, row in enumerate(matrix):
        for column_index, enabled in enumerate(row):
            if enabled:
                cell_x = x + (column_index * cell)
                cell_y = y + size - ((row_index + 1) * cell)
                commands.append(f"{cell_x:.2f} {cell_y:.2f} {cell:.2f} {cell:.2f} re f")
    return commands


def build_simple_pdf(title: str, lines: list[str], qr_payload: str | None = None) -> bytes:
    text_lines = [title, ""] + lines
    stream_lines = ["BT", "/F1 16 Tf", "72 760 Td", "20 TL"]
    for line in text_lines:
        stream_lines.append(f"({_escape_pdf_text(line)}) Tj")
        stream_lines.append("T*")
    stream_lines.append("ET")
    if qr_payload:
        stream_lines.extend(_qr_pdf_commands(qr_payload))
        stream_lines.extend([
            "BT",
            "/F1 9 Tf",
            "404 590 Td",
            "(QR verification centre) Tj",
            "ET",
        ])
    stream = "\n".join(stream_lines).encode("latin-1", "replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode())
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode())
    return bytes(pdf)


def build_convocation_pdf(convocation: dict) -> bytes:
    candidate = convocation["candidate"]
    session = convocation["session"]
    center = convocation["center"]
    lines = [
        "Document administratif - Convocation candidat",
        f"Reference convocation: {convocation['reference']}",
        f"Date emission: {convocation.get('issued_at', 'non renseignee')}",
        "",
        "1. Identite candidat",
        f"Reference candidat: {candidate['reference']}",
        f"Nom complet: {candidate['full_name']}",
        f"Identite: {candidate['identity_number']}",
        f"Telephone: {candidate['phone']}",
        f"Categorie permis: {candidate['permit_category']}",
        "",
        "2. Session d examen",
        f"Reference session: {session['reference']}",
        f"Date examen: {session['starts_at']}",
        f"Centre agree: {center['name']} ({center['code']})",
        f"Ville: {center['city']}",
        f"Adresse: {center['address']}",
        "",
        "3. Controle d entree",
        f"Code verification: {convocation['verification_code']}",
        f"Empreinte QR: {convocation['qr_payload']}",
        "Statut attendu: piece identite originale + convocation QR",
        "",
        "4. Consignes candidat",
        "Se presenter 30 minutes avant l heure de session.",
        "Presenter une piece d identite officielle en cours de validite.",
        "Tout retard, substitution ou tentative de fraude peut entrainer un refus d entree.",
        "Document verifiable par le centre agree via CodeRoute Guinee.",
    ]
    return build_simple_pdf("CodeRoute Guinee - Convocation officielle", lines, qr_payload=convocation["qr_payload"])


def build_result_certificate_pdf(candidate: dict, session: dict, center: dict, attempt: dict) -> bytes:
    decision = "ADMIS" if attempt.get("passed") else "NON ADMIS"
    lines = [
        f"Decision: {decision}",
        f"Reference candidat: {candidate['reference']}",
        f"Candidat: {candidate['full_name']}",
        f"Identite: {candidate['identity_number']}",
        f"Categorie permis: {candidate['permit_category']}",
        f"Session: {session['reference']}",
        f"Date examen: {session['starts_at']}",
        f"Centre: {center['name']}",
        f"Ville: {center['city']}",
        f"Score: {attempt.get('score')}",
        f"Statut tentative: {attempt.get('status')}",
        f"Date soumission: {attempt.get('submitted_at')}",
        "Document genere par CodeRoute Guinee pour verification administrative.",
    ]
    return build_simple_pdf("CodeRoute Guinee - Attestation de resultat", lines)


def _format_status_counts(label: str, values: dict[str, int]) -> list[str]:
    if not values:
        return [f"{label}: aucune donnee consolidee"]
    return [f"{label} - {status}: {count}" for status, count in sorted(values.items())]


def build_institutional_report_pdf(report: dict) -> bytes:
    recommendations = report.get("recommendations") or []
    lines = [
        "Document administratif - Rapport institutionnel",
        f"Destinataire: {report['generated_for']}",
        f"Score maturite: {report['readiness_score']}%",
        f"Statut: {report['readiness_label']}",
        f"Candidats references: {report['candidates']}",
        f"Evenements d audit: {report['audit_events']}",
        "",
        "1. Synthese nationale",
        "Plateforme de pilotage du code de la route: candidats, centres, examens, finances, audit et antifraude.",
        "Objectif: permettre une decision de pilote national avec indicateurs, preuves et actions suivies.",
        "",
        "2. Indicateurs consolides",
        *_format_status_counts("Centres", report.get("centers_by_status", {})),
        *_format_status_counts("Questions", report.get("questions_by_status", {})),
        *_format_status_counts("Identites", report.get("identity_checks_by_status", {})),
        *_format_status_counts("Habilitations", report.get("authorizations_by_status", {})),
        "",
        "3. Recommandations prioritaires",
        *[f"{index}. {recommendation}" for index, recommendation in enumerate(recommendations[:6], start=1)],
        "",
        "4. Decision proposee",
        "Valider un pilote institutionnel encadre avec centres retenus, donnees officielles limitees, supervision nationale et rapport hebdomadaire.",
        "Document genere par CodeRoute Guinee pour presentation administrative et suivi de mise en production.",
    ]
    return build_simple_pdf("CodeRoute Guinee - Rapport institutionnel", lines)
