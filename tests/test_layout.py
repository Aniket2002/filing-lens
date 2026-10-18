import pymupdf

from filing_lens.table_layout import statement_table


def make_page(title):
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((40, 50), title)
    page.insert_text((40, 70), "In millions, except per share amounts")
    page.insert_text((330, 90), "2023")
    page.insert_text((450, 90), "2022")
    for idx, (label, a, b) in enumerate(
        [
            ("Revenue", "100", "90"),
            ("Cost of sales", "60", "50"),
            ("Research and development", "10", "8"),
            ("Net income", "(5)", "6"),
            ("Total assets", "200", "190"),
        ]
    ):
        y = 115 + idx * 20
        page.insert_text((40, y), label)
        page.insert_text((330, y), a)
        page.insert_text((450, y), b)
    return document, page


def test_borderless_layout_extraction_uses_year_columns_and_retains_negative_sign():
    document, page = make_page("Consolidated Statements of Income")
    table = statement_table(page, "EXAMPLE-2023")
    assert table["years"] == [2023, 2022]
    assert table["unit"] == "USD_millions"
    assert table["rows"][4] == ["Net income", "(5)", "6"]
    document.close()


def test_narrative_mention_of_a_statement_is_not_a_statement_heading():
    document, page = make_page("Please refer to our Consolidated Statements of Income")
    assert statement_table(page, "EXAMPLE-2023") is None
    document.close()
