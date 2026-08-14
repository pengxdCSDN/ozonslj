from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from backend.app.domain.keyword_import import parse_keyword_xlsx


def test_keyword_xlsx_mapping_normalizes_external_headers() -> None:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        xml = (
            "<worksheet><sheetData><row><c><v>词</v></c><c><v>量</v></c><c><v>率</v></c></row>"
            "<row><c><v>термос</v></c><c><v>8</v></c><c><v>1%</v></c></row>"
            "</sheetData></worksheet>"
        )
        archive.writestr("xl/worksheets/sheet1.xml", xml)
    rows = parse_keyword_xlsx(
        output.getvalue(), {"词": "keyword", "量": "search_count", "率": "conversion_rate"}
    )
    assert rows[0].search_count == 8
