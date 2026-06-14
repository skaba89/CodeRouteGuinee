def _escape_pdf_text(value: object) -> str:
    text = str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text.encode("latin-1", "replace").decode("latin-1")


def build_simple_pdf(title: str, lines: list[str]) -> bytes:
    text_lines = [title, ""] + lines
    stream_lines = ["BT", "/F1 16 Tf", "72 760 Td", "20 TL"]
    for line in text_lines:
        stream_lines.append(f"({_escape_pdf_text(line)}) Tj")
        stream_lines.append("T*")
    stream_lines.append("ET")
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
        f"Reference: {convocation['reference']}",
        f"Candidat: {candidate['full_name']}",
        f"Identite: {candidate['identity_number']}",
        f"Telephone: {candidate['phone']}",
        f"Categorie permis: {candidate['permit_category']}",
        f"Session: {session['reference']}",
        f"Date examen: {session['starts_at']}",
        f"Centre: {center['name']}",
        f"Ville: {center['city']}",
        f"Adresse: {center['address']}",
        f"Verification: {convocation['verification_code']}",
        f"QR payload: {convocation['qr_payload']}",
        "Instruction: presenter cette convocation et une piece d'identite au centre agree.",
    ]
    return build_simple_pdf("CodeRoute Guinee - Convocation officielle", lines)


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
