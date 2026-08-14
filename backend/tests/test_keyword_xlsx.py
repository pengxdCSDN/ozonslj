from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from backend.app.domain.keyword_import import parse_keyword_xlsx


def test_keyword_xlsx_import_reads_first_sheet() -> None:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        xml = (
            "<worksheet><sheetData><row><c><v>keyword</v></c>"
            "<c><v>search_count</v></c><c><v>conversion_rate</v></c></row>"
            "<row><c><v>термос</v></c><c><v>12</v></c><c><v>2%</v></c></row>"
            "</sheetData></worksheet>"
        )
        archive.writestr("xl/worksheets/sheet1.xml", xml)
    rows = parse_keyword_xlsx(output.getvalue())
    assert rows[0].keyword == "термос"
