from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from lxml import etree


MATHML_NS = "http://www.w3.org/1998/Math/MathML"
OMML_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
XML_NS = "http://www.w3.org/XML/1998/namespace"


class FormulaConversionError(RuntimeError):
    pass


@dataclass(frozen=True)
class FormulaToken:
    latex: str
    display: bool
    start: int
    end: int


INLINE_MATH_RE = re.compile(
    r"(?<!\\)(?:\\\((?P<paren>.+?)\\\)|(?<!\$)\$(?!\$)(?P<dollar>.+?)(?<!\\)\$(?!\$))",
    flags=re.DOTALL,
)


def _local_name(node: etree._Element) -> str:
    return etree.QName(node).localname


def _omml(tag: str, *, value: str | None = None) -> etree._Element:
    element = etree.Element(f"{{{OMML_NS}}}{tag}")
    if value is not None:
        element.set(f"{{{OMML_NS}}}val", value)
    return element


def _append_all(parent: etree._Element, children: Iterable[etree._Element]) -> etree._Element:
    for child in children:
        parent.append(child)
    return parent


def _text_run(text: str, *, plain: bool = False, bold: bool = False) -> etree._Element:
    run = _omml("r")
    if plain or bold:
        run_properties = _omml("rPr")
        run_properties.append(_omml("sty", value="b" if bold else "p"))
        run.append(run_properties)
    text_node = _omml("t")
    text_node.set(f"{{{XML_NS}}}space", "preserve")
    text_node.text = text
    run.append(text_node)
    return run


def _slot(tag: str, node: etree._Element | None) -> etree._Element:
    slot = _omml(tag)
    if node is not None:
        _append_all(slot, _convert_node(node))
    return slot


def _node_text(node: etree._Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext())


def _container(node: etree._Element) -> list[etree._Element]:
    result: list[etree._Element] = []
    if node.text and node.text.strip():
        result.append(_text_run(node.text))
    for child in node:
        result.extend(_convert_node(child))
        if child.tail and child.tail.strip():
            result.append(_text_run(child.tail))
    return result


def _convert_fraction(node: etree._Element) -> list[etree._Element]:
    children = list(node)
    fraction = _omml("f")
    fraction.append(_slot("num", children[0] if len(children) > 0 else None))
    fraction.append(_slot("den", children[1] if len(children) > 1 else None))
    return [fraction]


def _convert_script(node: etree._Element, kind: str) -> list[etree._Element]:
    children = list(node)
    script = _omml(kind)
    script.append(_slot("e", children[0] if children else None))
    if kind in {"sSub", "sSubSup"}:
        script.append(_slot("sub", children[1] if len(children) > 1 else None))
    if kind == "sSup":
        script.append(_slot("sup", children[1] if len(children) > 1 else None))
    elif kind == "sSubSup":
        script.append(_slot("sup", children[2] if len(children) > 2 else None))
    return [script]


def _convert_radical(node: etree._Element, *, indexed: bool) -> list[etree._Element]:
    children = list(node)
    radical = _omml("rad")
    properties = _omml("radPr")
    if not indexed:
        properties.append(_omml("degHide", value="1"))
    radical.append(properties)
    if indexed:
        radical.append(_slot("deg", children[1] if len(children) > 1 else None))
    else:
        radical.append(_omml("deg"))
    radical.append(_slot("e", children[0] if children else None))
    return [radical]


def _convert_fenced(node: etree._Element) -> list[etree._Element]:
    delimiter = _omml("d")
    properties = _omml("dPr")
    properties.append(_omml("begChr", value=node.get("open", "(")))
    properties.append(_omml("endChr", value=node.get("close", ")")))
    separators = node.get("separators", ",")
    if separators:
        properties.append(_omml("sepChr", value=separators[0]))
    delimiter.append(properties)
    delimiter.append(_append_all(_omml("e"), _container(node)))
    return [delimiter]


def _convert_over_under(node: etree._Element, *, over: bool, under: bool) -> list[etree._Element]:
    children = list(node)
    base = children[0] if children else None
    lower = children[1] if under and len(children) > 1 else None
    upper_index = 2 if under else 1
    upper = children[upper_index] if over and len(children) > upper_index else None

    if over and not under:
        accent = _node_text(upper).strip()
        if node.get("accent") == "true" or accent in {"¯", "‾", "^", "ˆ", "→", "˙", "~", "˜"}:
            element = _omml("acc")
            properties = _omml("accPr")
            properties.append(_omml("chr", value=accent or "¯"))
            element.append(properties)
            element.append(_slot("e", base))
            return [element]

    if over and under:
        element = _omml("sSubSup")
        element.append(_slot("e", base))
        element.append(_slot("sub", lower))
        element.append(_slot("sup", upper))
        return [element]

    kind = "limUpp" if over else "limLow"
    element = _omml(kind)
    element.append(_slot("e", base))
    element.append(_slot("lim", upper if over else lower))
    return [element]


def _convert_matrix(node: etree._Element) -> list[etree._Element]:
    matrix = _omml("m")
    for row_node in node:
        if _local_name(row_node) != "mtr":
            continue
        row = _omml("mr")
        for cell_node in row_node:
            if _local_name(cell_node) != "mtd":
                continue
            row.append(_append_all(_omml("e"), _container(cell_node)))
        matrix.append(row)
    return [matrix]


def _convert_node(node: etree._Element) -> list[etree._Element]:
    name = _local_name(node)
    if name in {"math", "mrow", "mstyle", "semantics", "mpadded", "mphantom", "mtd"}:
        children = list(node)
        if name == "semantics" and children:
            return _convert_node(children[0])
        return _container(node)
    if name in {"annotation", "annotation-xml"}:
        return []
    if name in {"mi", "mn", "mo", "mtext", "ms"}:
        text = _node_text(node)
        plain = name in {"mtext", "ms"} or node.get("mathvariant") == "normal"
        bold = node.get("mathvariant") in {"bold", "bold-italic"}
        return [_text_run(text, plain=plain, bold=bold)] if text else []
    if name == "mspace":
        return [_text_run(" ", plain=True)]
    if name == "mfrac":
        return _convert_fraction(node)
    if name == "msup":
        return _convert_script(node, "sSup")
    if name == "msub":
        return _convert_script(node, "sSub")
    if name == "msubsup":
        return _convert_script(node, "sSubSup")
    if name == "msqrt":
        return _convert_radical(node, indexed=False)
    if name == "mroot":
        return _convert_radical(node, indexed=True)
    if name == "mfenced":
        return _convert_fenced(node)
    if name == "mover":
        return _convert_over_under(node, over=True, under=False)
    if name == "munder":
        return _convert_over_under(node, over=False, under=True)
    if name == "munderover":
        return _convert_over_under(node, over=True, under=True)
    if name == "mtable":
        return _convert_matrix(node)
    if name == "menclose":
        box = _omml("borderBox")
        box.append(_append_all(_omml("e"), _container(node)))
        return [box]
    return _container(node)


def normalize_latex(latex: str) -> str:
    value = latex.strip()
    value = re.sub(r"\\(?:label|tag)\s*\{[^{}]*\}", "", value)
    value = value.rstrip(".")
    return value.strip()


def latex_to_omml(latex: str) -> etree._Element:
    normalized = normalize_latex(latex)
    if not normalized:
        raise FormulaConversionError("formula is empty")
    try:
        from latex2mathml.converter import convert
    except Exception as exc:
        raise FormulaConversionError("latex2mathml is required for native Word equations") from exc
    try:
        mathml = convert(normalized)
        root = etree.fromstring(mathml.encode("utf-8"))
        content = _convert_node(root)
    except Exception as exc:
        raise FormulaConversionError(f"LaTeX conversion failed for {normalized!r}: {exc}") from exc
    if not content:
        raise FormulaConversionError(f"LaTeX conversion produced no OMML content for {normalized!r}")
    equation = _omml("oMath")
    _append_all(equation, content)
    return equation


def display_omml(latex: str) -> etree._Element:
    paragraph = _omml("oMathPara")
    properties = _omml("oMathParaPr")
    properties.append(_omml("jc", value="center"))
    paragraph.append(properties)
    paragraph.append(latex_to_omml(latex))
    return paragraph


def inline_formula_tokens(text: str) -> list[FormulaToken]:
    tokens: list[FormulaToken] = []
    for match in INLINE_MATH_RE.finditer(text):
        latex = match.group("paren") if match.group("paren") is not None else match.group("dollar")
        tokens.append(FormulaToken(latex=latex or "", display=False, start=match.start(), end=match.end()))
    return tokens


def source_formula_tokens(text: str) -> list[FormulaToken]:
    tokens: list[FormulaToken] = []
    display_spans: list[tuple[int, int]] = []
    for match in re.finditer(r"(?<!\\)\$\$(.+?)(?<!\\)\$\$|\\\[(.+?)\\\]", text, flags=re.DOTALL):
        latex = match.group(1) if match.group(1) is not None else match.group(2)
        tokens.append(FormulaToken(latex=(latex or "").strip(), display=True, start=match.start(), end=match.end()))
        display_spans.append((match.start(), match.end()))

    masked = list(text)
    for start, end in display_spans:
        masked[start:end] = " " * (end - start)
    masked_text = "".join(masked)
    tokens.extend(inline_formula_tokens(masked_text))
    return sorted(tokens, key=lambda item: item.start)
