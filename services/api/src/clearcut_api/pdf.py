import re
import textwrap
import unicodedata
from dataclasses import dataclass, field

PAGE_WIDTH = 612
PAGE_HEIGHT = 792
MARGIN = 48


@dataclass
class SummaryRow:
    asset: str
    category: str
    status: str
    risk: str
    confidence: str
    evidence: int


@dataclass
class EvidenceItem:
    title: str
    url: str
    excerpt: str


@dataclass
class Decision:
    asset: str
    decision: str
    actor: str
    recorded: str
    note: str


@dataclass
class PermissionWork:
    asset: str
    status: str
    recipient: str
    due: str
    subject: str


@dataclass
class Detail:
    name: str
    category: str = ""
    scene: str = ""
    context: str = ""
    status: str = "-"
    risk: str = "-"
    confidence: str = "-"
    summary: str = ""
    recommendation: str = ""
    reason_codes: list[str] = field(default_factory=list)
    evidence: list[EvidenceItem] = field(default_factory=list)


@dataclass
class ParsedReport:
    title: str
    metadata: dict[str, str]
    notice: str
    summary_rows: list[SummaryRow]
    details: list[Detail]
    decisions: list[Decision]
    permissions: list[PermissionWork]


def _clean(value: str) -> str:
    return value.replace("`", "").replace("**", "").strip()


def _table_cells(line: str) -> list[str]:
    return [_clean(cell) for cell in line.strip("|").split("|")]


def _parse_report(markdown: str) -> ParsedReport:
    parsed = ParsedReport(
        title="Clearance report",
        metadata={},
        notice=(
            "ClearCut provides research and workflow support. This report is not legal advice "
            "and does not declare any asset legally cleared."
        ),
        summary_rows=[],
        details=[],
        decisions=[],
        permissions=[],
    )
    in_summary_table = False
    in_details = False
    in_decision_log = False
    in_permission_work = False
    current: Detail | None = None

    lines = markdown.splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("# "):
            parsed.title = re.sub(
                r"^ClearCut clearance report\s*[—-]\s*", "", _clean(line[2:]), flags=re.IGNORECASE
            )
        elif not in_summary_table and not in_details and line.startswith("- "):
            metadata = re.match(r"^- ([^:]+):\s*(.*)$", line)
            if metadata:
                parsed.metadata[metadata.group(1).strip().lower()] = _clean(metadata.group(2))
        elif line.startswith("> "):
            parsed.notice = _clean(line[2:])
        elif line == "## Asset summary":
            in_summary_table = True
            in_details = False
            in_decision_log = False
            in_permission_work = False
        elif line == "## Detailed review":
            in_summary_table = False
            in_details = True
            in_decision_log = False
            in_permission_work = False
        elif line == "## Decision log":
            if current is not None:
                parsed.details.append(current)
                current = None
            in_summary_table = False
            in_details = False
            in_decision_log = True
            in_permission_work = False
        elif line == "## Permission work":
            if current is not None:
                parsed.details.append(current)
                current = None
            in_summary_table = False
            in_details = False
            in_decision_log = False
            in_permission_work = True
        elif line == "## Method and limitations":
            in_summary_table = False
            in_details = False
            in_decision_log = False
            in_permission_work = False
        elif in_summary_table and line.startswith("|"):
            if "| Asset |" in line:
                continue
            cells = _table_cells(line)
            if len(cells) >= 6 and cells[0] and not cells[0].startswith("---"):
                try:
                    evidence = int(cells[5])
                except ValueError:
                    evidence = 0
                parsed.summary_rows.append(
                    SummaryRow(
                        asset=cells[0],
                        category=cells[1],
                        status=cells[2] or "-",
                        risk=cells[3] or "-",
                        confidence=cells[4] or "-",
                        evidence=evidence,
                    )
                )
        elif in_decision_log and line.startswith("|"):
            if "| Asset | Decision |" in line:
                continue
            cells = _table_cells(line)
            if len(cells) >= 5 and cells[0] and not cells[0].startswith("---"):
                parsed.decisions.append(
                    Decision(
                        asset=cells[0],
                        decision=cells[1],
                        actor=cells[2],
                        recorded=cells[3],
                        note=cells[4],
                    )
                )
        elif in_permission_work and line.startswith("|"):
            if "| Asset | Status |" in line:
                continue
            cells = _table_cells(line)
            if len(cells) >= 5 and cells[0] and not cells[0].startswith("---"):
                parsed.permissions.append(
                    PermissionWork(
                        asset=cells[0],
                        status=cells[1],
                        recipient=cells[2],
                        due=cells[3],
                        subject=cells[4],
                    )
                )
        elif in_details and line.startswith("### "):
            if current is not None:
                parsed.details.append(current)
            current = Detail(name=_clean(line[4:]))
        elif current is not None:
            if line.startswith("- Category:"):
                current.category = _clean(line[11:])
            elif line.startswith("- Scene:"):
                current.scene = _clean(line[8:])
            elif line.startswith("- Context:"):
                current.context = _clean(line[10:])
            elif line.startswith("- Current asset status:"):
                current.status = _clean(line[23:])
            elif line.startswith("- Clearance card status:"):
                current.status = _clean(line[24:])
            elif line.startswith("- Risk score:"):
                current.risk = _clean(line[13:])
            elif line.startswith("- Confidence:"):
                current.confidence = _clean(line[13:])
            elif line.startswith("- Summary:"):
                current.summary = _clean(line[10:])
            elif line.startswith("- Recommended next action:"):
                current.recommendation = _clean(line[27:])
            elif line.startswith("- Reason codes:"):
                current.reason_codes = [
                    code.strip() for code in _clean(line[15:]).split(",") if code.strip()
                ]
            elif line.startswith("- ["):
                source = re.match(r"^- \[([^\]]+)\]\(([^)]+)\)\s+—\s+(.*)$", line)
                if source:
                    current.evidence.append(
                        EvidenceItem(
                            title=source.group(1), url=source.group(2), excerpt=source.group(3)
                        )
                    )
    if current is not None:
        parsed.details.append(current)
    return parsed


def _ascii(value: str) -> str:
    normalized = (
        value.replace("—", " - ")
        .replace("–", "-")
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("…", "...")
    )
    return unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("ascii")


def _pdf_escape(value: str) -> str:
    value = _ascii(value).encode("latin-1", "replace").decode("latin-1")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _color(red: int, green: int, blue: int) -> str:
    return f"{red / 255:.3f} {green / 255:.3f} {blue / 255:.3f}"


class _PdfBuilder:
    def __init__(self, report: ParsedReport):
        self.report = report
        self.pages: list[list[str]] = []
        self.y = 0
        self.new_page(cover=True)

    @property
    def commands(self) -> list[str]:
        return self.pages[-1]

    def new_page(self, *, cover: bool = False) -> None:
        self.pages.append([])
        if cover:
            self.commands.extend(
                [
                    f"{_color(23, 23, 25)} rg",
                    f"0 0 {PAGE_WIDTH} {PAGE_HEIGHT} re f",
                    f"{_color(228, 184, 106)} rg",
                    f"0 {PAGE_HEIGHT - 6} {PAGE_WIDTH} 6 re f",
                ]
            )
            self.y = 690
        else:
            self.commands.extend(
                [
                    f"{_color(250, 248, 244)} rg",
                    f"0 0 {PAGE_WIDTH} {PAGE_HEIGHT} re f",
                    f"{_color(228, 184, 106)} rg",
                    f"{MARGIN} {PAGE_HEIGHT - 38} 58 3 re f",
                    f"{_color(55, 53, 57)} rg",
                    f"{MARGIN} {PAGE_HEIGHT - 58} m {PAGE_WIDTH - MARGIN} {PAGE_HEIGHT - 58} l S",
                ]
            )
            self.text("CLEARCUT / RIGHTS INTELLIGENCE", MARGIN, PAGE_HEIGHT - 50, 8, bold=True, color=_color(105, 100, 94))
            self.y = PAGE_HEIGHT - 86

    def ensure(self, height: int = 18) -> None:
        if self.y - height < 58:
            self.new_page()

    def text(self, value: str, x: int, y: int, size: int, *, bold: bool = False, color: str = "0 0 0") -> None:
        font = "/F2" if bold else "/F1"
        self.commands.extend(
            [
                f"{color} rg",
                "BT",
                f"{font} {size} Tf",
                f"{x} {y} Td",
                f"({_pdf_escape(value)}) Tj",
                "ET",
            ]
        )

    def rect(self, x: int, y: int, width: int, height: int, color: str, *, stroke: bool = False) -> None:
        self.commands.append(f"{color} {'RG' if stroke else 'rg'}")
        self.commands.append(f"{x} {y} {width} {height} re {'S' if stroke else 'f'}")

    def wrapped(self, value: str, *, x: int = MARGIN, size: int = 10, leading: int = 14, width: int = 88, color: str = "0 0 0", bold: bool = False) -> None:
        for line in textwrap.wrap(_ascii(value), width=width, break_long_words=False, break_on_hyphens=False) or [""]:
            self.ensure(leading)
            self.text(line, x, self.y, size, bold=bold, color=color)
            self.y -= leading

    def section(self, number: str, label: str, heading: str) -> None:
        self.ensure(50)
        self.text(number, MARGIN, self.y, 8, bold=True, color=_color(179, 138, 69))
        self.text(label.upper(), MARGIN + 23, self.y, 8, color=_color(126, 119, 109))
        self.y -= 18
        self.text(heading, MARGIN, self.y, 18, bold=True, color=_color(36, 35, 38))
        self.y -= 28

    def cover(self) -> None:
        self.text("C", MARGIN, self.y, 18, bold=True, color=_color(25, 20, 10))
        self.rect(MARGIN - 3, self.y - 7, 25, 25, _color(228, 184, 106))
        self.text("C", MARGIN + 4, self.y, 14, bold=True, color=_color(25, 20, 10))
        self.text("CLEARCUT", MARGIN + 34, self.y + 4, 14, bold=True, color=_color(246, 241, 232))
        self.text("RIGHTS INTELLIGENCE", MARGIN + 34, self.y - 9, 7, color=_color(155, 154, 157))
        self.y -= 130
        self.text("EVIDENCE-BACKED CLEARANCE REPORT", MARGIN, self.y, 9, bold=True, color=_color(228, 184, 106))
        self.y -= 29
        self.wrapped(self.report.title, x=MARGIN, size=30, leading=34, width=38, color=_color(246, 241, 232), bold=True)
        self.y -= 10
        self.wrapped("Production rights review prepared for human decision-making and distribution readiness.", x=MARGIN, size=11, leading=16, width=70, color=_color(183, 179, 173))
        self.y -= 55
        self.commands.extend([f"{_color(59, 57, 64)} RG", f"{MARGIN} {self.y} {PAGE_WIDTH - 2 * MARGIN} 1 re S"])
        self.y -= 23
        metadata = [("PROJECT TYPE", self.report.metadata.get("project type", "Not set")), ("GENERATED", self.report.metadata.get("generated", "Not set")), ("ASSETS REVIEWED", self.report.metadata.get("assets reviewed", "0")), ("REPORT STATE", "Human review required")]
        for index, (label, value) in enumerate(metadata):
            x = MARGIN + (index % 2) * 255
            y = self.y - (index // 2) * 46
            self.text(label, x, y, 7, color=_color(119, 116, 122))
            self.text(_ascii(value)[:42], x, y - 14, 10, bold=True, color=_color(246, 241, 232))
        self.text("REPORT SNAPSHOT", MARGIN, 85, 7, color=_color(119, 116, 122))
        self.text("HUMAN REVIEW REQUIRED", PAGE_WIDTH - MARGIN - 124, 85, 7, color=_color(228, 184, 106))

    def summary_table(self) -> None:
        self.ensure(40)
        columns = [(MARGIN, 120), (168, 70), (246, 92), (344, 58), (410, 67), (487, 77)]
        headers = ["ASSET", "CATEGORY", "STATUS", "RISK", "CONFIDENCE", "EVIDENCE"]
        row_height = 24
        self.rect(MARGIN, self.y - row_height + 4, PAGE_WIDTH - 2 * MARGIN, row_height, _color(41, 40, 43))
        for (x, _), header in zip(columns, headers, strict=True):
            self.text(header, x + 7, self.y - 10, 7, bold=True, color=_color(246, 241, 232))
        self.y -= row_height
        for index, row in enumerate(self.report.summary_rows):
            if self.y - row_height < 58:
                self.new_page()
                self.summary_table_header(columns, headers, row_height)
            if index % 2 == 0:
                self.rect(MARGIN, self.y - row_height + 4, PAGE_WIDTH - 2 * MARGIN, row_height, _color(239, 234, 225))
            values = [row.asset, row.category, row.status, row.risk, row.confidence, f"{row.evidence} sources"]
            for (x, width), value in zip(columns, values, strict=True):
                self.text(_ascii(value)[: max(10, width // 5)], x + 7, self.y - 10, 8, color=_color(75, 71, 67), bold=x == MARGIN)
            self.y -= row_height
        self.y -= 12

    def summary_table_header(self, columns: list[tuple[int, int]], headers: list[str], row_height: int) -> None:
        self.rect(MARGIN, self.y - row_height + 4, PAGE_WIDTH - 2 * MARGIN, row_height, _color(41, 40, 43))
        for (x, _), header in zip(columns, headers, strict=True):
            self.text(header, x + 7, self.y - 10, 7, bold=True, color=_color(246, 241, 232))
        self.y -= row_height

    def details(self) -> None:
        for detail in self.report.details:
            self.ensure(80)
            self.y -= 14
            self.rect(MARGIN, self.y - 6, 3, 54, _color(179, 138, 69))
            self.text(_ascii(detail.name)[:72], MARGIN + 14, self.y + 24, 13, bold=True, color=_color(36, 35, 38))
            self.text(_ascii(f"{detail.category} {(' - Scene ' + detail.scene) if detail.scene else ''}"), MARGIN + 14, self.y + 9, 8, color=_color(126, 119, 109))
            self.text(_ascii(detail.status), PAGE_WIDTH - MARGIN - 90, self.y + 18, 8, bold=True, color=_color(154, 110, 39))
            self.y -= 12
            if detail.context:
                self.text("SOURCE CONTEXT", MARGIN + 14, self.y, 7, color=_color(126, 119, 109))
                self.y -= 12
                self.wrapped(detail.context, x=MARGIN + 14, size=9, leading=12, width=84, color=_color(75, 71, 67))
            if detail.summary:
                self.y -= 5
                self.text("ASSESSMENT", MARGIN + 14, self.y, 7, color=_color(126, 119, 109))
                self.y -= 12
                self.wrapped(detail.summary, x=MARGIN + 14, size=9, leading=12, width=84, color=_color(75, 71, 67))
            if detail.recommendation:
                self.y -= 5
                self.text("RECOMMENDED NEXT ACTION", MARGIN + 14, self.y, 7, color=_color(126, 119, 109))
                self.y -= 12
                self.wrapped(detail.recommendation, x=MARGIN + 14, size=9, leading=12, width=84, color=_color(75, 71, 67))
            if detail.evidence:
                self.y -= 5
                self.text("EVIDENCE", MARGIN + 14, self.y, 7, color=_color(126, 119, 109))
                self.y -= 12
                for source in detail.evidence:
                    self.wrapped(f"{source.title} - {source.excerpt}", x=MARGIN + 18, size=8, leading=11, width=82, color=_color(71, 115, 155))
                    self.wrapped(source.url, x=MARGIN + 18, size=7, leading=9, width=92, color=_color(126, 119, 109))
            if detail.reason_codes:
                self.y -= 4
                self.wrapped(f"Reason codes: {', '.join(detail.reason_codes)}", x=MARGIN + 14, size=7, leading=10, width=90, color=_color(126, 119, 109))
            self.y -= 13
            self.commands.extend([f"{_color(216, 208, 195)} RG", f"{MARGIN} {self.y} {PAGE_WIDTH - 2 * MARGIN} 1 re S"])
            self.y -= 15

    def decisions(self) -> None:
        self.ensure(55)
        if not self.report.decisions:
            self.wrapped(
                "No human decisions have been recorded in this snapshot.",
                size=10,
                leading=14,
                width=88,
                color=_color(75, 71, 67),
            )
            return
        columns = [(MARGIN, 155), (215, 100), (322, 78), (410, 92), (510, 54)]
        headers = ["ASSET", "DECISION", "ACTOR", "RECORDED", "NOTE"]
        row_height = 24
        self.rect(MARGIN, self.y - row_height + 4, PAGE_WIDTH - 2 * MARGIN, row_height, _color(41, 40, 43))
        for (x, _), header in zip(columns, headers, strict=True):
            self.text(header, x + 7, self.y - 10, 7, bold=True, color=_color(246, 241, 232))
        self.y -= row_height
        for index, decision in enumerate(self.report.decisions):
            if self.y - row_height < 58:
                self.new_page()
                self.section("05", "Decision log", "Human accountability")
                self.rect(MARGIN, self.y - row_height + 4, PAGE_WIDTH - 2 * MARGIN, row_height, _color(41, 40, 43))
                for (x, _), header in zip(columns, headers, strict=True):
                    self.text(header, x + 7, self.y - 10, 7, bold=True, color=_color(246, 241, 232))
                self.y -= row_height
            if index % 2 == 0:
                self.rect(MARGIN, self.y - row_height + 4, PAGE_WIDTH - 2 * MARGIN, row_height, _color(239, 234, 225))
            values = [decision.asset, decision.decision, decision.actor, decision.recorded, decision.note]
            for (x, width), value in zip(columns, values, strict=True):
                self.text(_ascii(value)[: max(10, width // 5)], x + 7, self.y - 10, 7, color=_color(75, 71, 67), bold=x == MARGIN)
            self.y -= row_height
        self.y -= 12

    def permissions(self) -> None:
        self.ensure(55)
        if not self.report.permissions:
            self.wrapped(
                "No permission requests have been drafted in this snapshot.",
                size=10,
                leading=14,
                width=88,
                color=_color(75, 71, 67),
            )
            return
        columns = [(MARGIN, 150), (210, 82), (302, 112), (420, 82), (510, 54)]
        headers = ["ASSET", "STATUS", "RECIPIENT", "DUE", "SUBJECT"]
        row_height = 24
        self.rect(MARGIN, self.y - row_height + 4, PAGE_WIDTH - 2 * MARGIN, row_height, _color(41, 40, 43))
        for (x, _), header in zip(columns, headers, strict=True):
            self.text(header, x + 7, self.y - 10, 7, bold=True, color=_color(246, 241, 232))
        self.y -= row_height
        for index, permission in enumerate(self.report.permissions):
            if self.y - row_height < 58:
                self.new_page()
                self.section("04", "Permission work", "Requests and response state")
                self.rect(MARGIN, self.y - row_height + 4, PAGE_WIDTH - 2 * MARGIN, row_height, _color(41, 40, 43))
                for (x, _), header in zip(columns, headers, strict=True):
                    self.text(header, x + 7, self.y - 10, 7, bold=True, color=_color(246, 241, 232))
                self.y -= row_height
            if index % 2 == 0:
                self.rect(MARGIN, self.y - row_height + 4, PAGE_WIDTH - 2 * MARGIN, row_height, _color(239, 234, 225))
            values = [permission.asset, permission.status, permission.recipient, permission.due, permission.subject]
            for (x, width), value in zip(columns, values, strict=True):
                self.text(_ascii(value)[: max(10, width // 5)], x + 7, self.y - 10, 7, color=_color(75, 71, 67), bold=x == MARGIN)
            self.y -= row_height
        self.y -= 12

    def build(self) -> bytes:
        self.cover()
        self.new_page()
        self.section("01", "Executive summary", "Action and evidence at a glance")
        total = len(self.report.summary_rows)
        attention = sum(row.status not in {"approved", "complete"} for row in self.report.summary_rows)
        high_risk = sum(bool(re.search(r"[7-9]\d|100", row.risk)) for row in self.report.summary_rows)
        evidence = sum(row.evidence > 0 for row in self.report.summary_rows)
        kpis = [("ASSETS", str(total)), ("NEED ATTENTION", str(attention)), ("HIGH-RISK SIGNALS", str(high_risk)), ("EVIDENCE COVERAGE", f"{round(evidence / total * 100) if total else 0}%")]
        width = 123
        for index, (label, value) in enumerate(kpis):
            x = MARGIN + index * (width + 7)
            self.rect(x, self.y - 48, width, 48, _color(239, 234, 225))
            self.text(label, x + 9, self.y - 15, 7, color=_color(126, 119, 109))
            self.text(value, x + 9, self.y - 36, 17, bold=True, color=_color(36, 35, 38))
        self.y -= 68
        self.wrapped("This snapshot consolidates extracted rights-bearing assets, research evidence, model recommendations, and the current human-review boundary. Review unresolved issues before delivery.", size=10, leading=14, width=88, color=_color(75, 71, 67))
        self.section("02", "Asset register", "Every signal in scope")
        self.summary_table()
        self.section("03", "Detailed review", "Evidence and recommended action")
        self.details()
        self.section("04", "Permission work", "Requests and response state")
        self.permissions()
        self.section("05", "Decision log", "Human accountability")
        self.decisions()
        self.section("06", "Method and limitations", "What this snapshot means")
        self.wrapped(self.report.notice, size=10, leading=14, width=88, color=_color(75, 71, 67))
        self.wrapped("Evidence is retained as a research snapshot. Recheck unresolved or time-sensitive sources before distribution and record the final human decision in ClearCut.", size=10, leading=14, width=88, color=_color(75, 71, 67))
        for page in self.pages:
            if page is not self.pages[0]:
                page.extend([])
        return _serialize(self.pages)


def _serialize(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"]
    page_refs: list[int] = []
    for page_number, commands in enumerate(pages, start=1):
        if page_number > 1:
            commands.extend(
                [
                    f"{_color(126, 119, 109)} rg",
                    "BT",
                    "/F1 7 Tf",
                    f"{MARGIN} 31 Td",
                    "(CLEARCUT / CONFIDENTIAL WORKFLOW RECORD) Tj",
                    "ET",
                    "BT",
                    "/F2 8 Tf",
                    f"{PAGE_WIDTH - MARGIN - 8} 31 Td",
                    f"({page_number - 1}) Tj",
                    "ET",
                ]
            )
        stream = "\n".join(commands).encode("latin-1", "replace")
        content_number = len(objects) + 1
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
        page_number_ref = len(objects) + 1
        objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents " + str(content_number).encode() + b" 0 R >>")
        page_refs.append(page_number_ref)
    kids = b"[" + b" ".join(str(ref).encode() + b" 0 R" for ref in page_refs) + b"]"
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
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode())
    return bytes(output)


def build_pdf(markdown: str) -> bytes:
    """Build a branded, dependency-free PDF snapshot for a clearance report."""
    return _PdfBuilder(_parse_report(markdown)).build()
