from apps.api.app.integrations.notebooklm.parser import parse_notebooklm_response


def test_parser_extracts_answer_and_citations_block() -> None:
    content = """Summary line.

CITATIONS:
- CSRD Directive | Art 19a | https://eur-lex.europa.eu | Core disclosure requirement
- ESRS 1 | Section 3.2 |  | Materiality process
"""
    parsed = parse_notebooklm_response(content)
    assert parsed.answer_markdown == "Summary line."
    assert len(parsed.citations) == 2
    assert parsed.citations[0].source_title == "CSRD Directive"
    assert parsed.citations[0].locator == "Art 19a"
    assert parsed.citations[0].url == "https://eur-lex.europa.eu"
    assert parsed.citations[1].source_title == "ESRS 1"
    assert parsed.citations[1].quote == "Materiality process"


def test_parser_without_citations_block_returns_empty_citations() -> None:
    parsed = parse_notebooklm_response("No citations included.")
    assert parsed.answer_markdown == "No citations included."
    assert parsed.citations == []
