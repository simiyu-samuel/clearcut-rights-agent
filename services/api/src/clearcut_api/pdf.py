import re
import textwrap


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _report_lines(markdown: str) -> list[str]:
    lines: list[str] = []
    for raw_line in markdown.splitlines():
        line = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", raw_line)
        line = line.replace("|", "  |  ").replace("`", "")
        if line.startswith("#"):
            line = line.lstrip("# ").upper()
        elif line.startswith("> "):
            line = "NOTE: " + line[2:]
        elif line.startswith("- "):
            line = "• " + line[2:]
        wrapped = textwrap.wrap(line, width=96, break_long_words=False, break_on_hyphens=False)
        lines.extend(wrapped or [""])
    return lines


def build_pdf(markdown: str) -> bytes:
    """Build a small, dependency-free PDF for downloadable clearance reports."""
    lines = _report_lines(markdown)
    lines_per_page = 54
    pages = [lines[index : index + lines_per_page] for index in range(0, len(lines), lines_per_page)]
    if not pages:
        pages = [[]]

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_refs: list[int] = []

    for page_lines in pages:
        commands = ["BT", "/F1 9 Tf", "54 742 Td", "12 TL"]
        for line in page_lines:
            safe_line = line.encode("latin-1", "replace").decode("latin-1")
            commands.append(f"({_pdf_escape(safe_line)}) Tj T*")
        commands.append("ET")
        stream = "\n".join(commands).encode("latin-1")
        content_number = len(objects) + 1
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page_number = len(objects) + 1
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 3 0 R >> >> /Contents "
            + str(content_number).encode()
            + b" 0 R >>"
        )
        page_refs.append(page_number)

    kids = b"[" + b" ".join(str(number).encode() + b" 0 R" for number in page_refs) + b"]"
    objects[1] = b"<< /Type /Pages /Kids " + kids + b" /Count " + str(len(page_refs)).encode() + b" >>"

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return bytes(output)
