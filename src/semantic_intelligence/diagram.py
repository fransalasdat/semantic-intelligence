"""Standalone SVG of model metadata. No row data, external renderer, or AI."""

from html import escape
import textwrap

from semantic_intelligence.relationship_semantics import effective_settings, filter_explanation


COLORS = ("#0f766e", "#2563eb", "#9333ea", "#b45309", "#be185d")
CARD_WIDTH, GUTTER, MARGIN, TOP, GAP = 360, 145, 38, 110, 36


def _wrapped(value, width=32):
    return textwrap.wrap(str(value), width, break_long_words=True, break_on_hyphens=False) or [""]


def render_er_svg(inventory, *, related_only=False, show_measures=True, selected_tables=None) -> str:
    """Show effective endpoint cardinalities; arrows represent filter propagation."""
    selected = set(selected_tables) if selected_tables is not None else {t.name for t in inventory.tables}
    tables = [t for t in inventory.tables if t.name in selected]
    relations = [r for r in inventory.relationships
                 if r.from_column.table in selected and r.to_column.table in selected]
    if not tables:
        raise ValueError("Seleccioná al menos una tabla para el diagrama.")
    endpoints = {(endpoint.table, endpoint.column) for r in inventory.relationships
                 for endpoint in (r.from_column, r.to_column)}
    cards = {}
    degree = {t.name: sum(t.name in (r.from_column.table, r.to_column.table) for r in relations) for t in tables}
    for table in tables:
        title = _wrapped(table.name)
        y = 20 + len(title) * 23 + 23
        header = y
        rows, ports = [], {}
        for column in table.columns:
            if related_only and (table.name, column.name) not in endpoints:
                continue
            lines = _wrapped(column.name, 28)
            height = max(30, 16 * len(lines) + 12)
            ports[column.name] = y + height / 2
            rows.append((y, height, lines, column.data_type or "—", False,
                         (table.name, column.name) in endpoints, column.name))
            y += height
        if show_measures:
            for measure in table.measures:
                lines = _wrapped(measure.name, 30)
                height = max(30, 16 * len(lines) + 12)
                rows.append((y, height, lines, "DAX", True, False, measure.name))
                y += height
        cards[table.name] = {"title": title, "header": header, "rows": rows, "ports": ports,
                            "height": y + 10, "table": table}

    center = max(tables, key=lambda table: degree[table.name]).name
    left, right = [], []
    for table in tables:
        if table.name == center:
            continue
        # Balance card heights rather than only table counts.
        group = right if len(tables) == 2 else min((left, right), key=lambda group: sum(cards[n]["height"] + GAP for n in group))
        group.append(table.name)
    side_height = lambda group: sum(cards[n]["height"] for n in group) + max(0, len(group) - 1) * GAP
    content_height = max(cards[center]["height"], side_height(left), side_height(right))
    center_x = MARGIN + (CARD_WIDTH + GUTTER if left else 0)
    cards[center]["position"] = (center_x, TOP + (content_height - cards[center]["height"]) / 2)
    for group, x in ((left, MARGIN), (right, center_x + CARD_WIDTH + GUTTER)):
        y = TOP + (content_height - side_height(group)) / 2
        for name in group:
            cards[name]["position"] = (x, y)
            y += cards[name]["height"] + GAP
    width = center_x + CARD_WIDTH + MARGIN + (CARD_WIDTH + GUTTER if right else 0)
    if any(r.from_column.table == r.to_column.table for r in relations):
        width += 100
    height = TOP + content_height + 88
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
           f'<title id="title">Modelo semántico: {escape(inventory.name)}</title>',
           '<desc id="desc">Tablas, columnas, tipos, medidas y relaciones. Flechas de propagación de filtros; líneas discontinuas para relaciones inactivas.</desc>',
           '<defs>']
    for i, color in enumerate(COLORS):
        svg.append(f'<marker id="arrow{i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{color}"/></marker>')
    svg.extend(['</defs>', f'<rect width="{width}" height="{height}" fill="#f8fafc"/>',
                '<g font-family="Segoe UI,Arial,sans-serif">',
                f'<text x="{MARGIN}" y="40" font-size="23" font-weight="700" fill="#152832">Diagrama del modelo</text>',
                f'<text x="{MARGIN}" y="67" font-size="14" fill="#526879">{escape(inventory.name)} · {len(tables)} tablas · {len(relations)} relaciones</text>'])
    for index, relationship in enumerate(relations):
        start, end = cards[relationship.from_column.table], cards[relationship.to_column.table]
        sx, sy = start["position"]
        ex, ey = end["position"]
        forward = sx < ex or start is end
        x1, x2 = sx + (CARD_WIDTH if forward else 0), ex + (0 if forward else CARD_WIDTH)
        y1 = sy + start["ports"][relationship.from_column.column]
        y2 = ey + end["ports"][relationship.to_column.column]
        settings = {v["key"]: v["value"].casefold() for v in effective_settings(relationship)}
        active = settings["isActive"] == "true"
        inactive = settings["isActive"] == "false"
        color_index = index % len(COLORS)
        color = COLORS[color_index] if active else "#94a3b8"
        direction = settings["crossFilteringBehavior"]
        markers = f' marker-start="url(#arrow{color_index})"' if active and direction in {"onedirection", "bothdirections"} else ""
        if active and direction == "bothdirections":
            markers += f' marker-end="url(#arrow{color_index})"'
        dash = ' stroke-dasharray="7 5"' if inactive else ''
        if start is end:
            x2 = ex + CARD_WIDTH
            bend = x1 + 50 + index * 8
            path = f'M {x1} {y1} C {bend} {y1 - 38}, {bend} {y2 + 38}, {x2} {y2}'
        else:
            middle = (x1 + x2) / 2 + (index % 3 - 1) * 14
            path = f'M {x1} {y1} C {middle} {y1}, {middle} {y2}, {x2} {y2}'
        description = (f'{relationship.from_column.table}[{relationship.from_column.column}] ↔ '
                       f'{relationship.to_column.table}[{relationship.to_column.column}]. '
                       + filter_explanation(relationship))
        svg.append(f'<g><title>{escape(description)}</title><path d="{path}" fill="none" stroke="{color}" stroke-width="2.1"{dash}{markers}/>')
        for x, y, value, offset in ((x1, y1, settings["fromCardinality"], 19 if forward else -19),
                                    (x2, y2, settings["toCardinality"], -19 if forward else 19)):
            symbol = {"one": "1", "many": "*"}.get(value, "?")
            svg.append(f'<rect x="{x + offset - 9}" y="{y - 19}" width="18" height="18" rx="4" fill="#f8fafc"/><text x="{x + offset}" y="{y - 5}" text-anchor="middle" fill="{color}" font-size="15" font-weight="700">{symbol}</text>')
        svg.append('</g>')

    for card in cards.values():
        x, y = card["position"]
        svg.append(f'<g transform="translate({x},{y})"><rect x="2" y="4" width="{CARD_WIDTH}" height="{card["height"]}" rx="12" fill="#dbe5ea"/><rect width="{CARD_WIDTH}" height="{card["height"]}" rx="12" fill="white" stroke="#cbd5e1"/>')
        svg.append(f'<path d="M 12 0 H {CARD_WIDTH-12} Q {CARD_WIDTH} 0 {CARD_WIDTH} 12 V {card["header"]} H 0 V 12 Q 0 0 12 0" fill="#0f766e"/>')
        for i, line in enumerate(card["title"]):
            svg.append(f'<text x="16" y="{29 + i * 23}" fill="white" font-size="17" font-weight="600">{escape(line)}</text>')
        table = card["table"]
        svg.append(f'<text x="16" y="{card["header"] - 12}" fill="#ccfbf1" font-size="12">{len(table.columns)} columnas · {len(table.measures)} medidas</text>')
        for row_y, row_h, lines, dtype, measure, related, full_name in card["rows"]:
            fill = "#faf5ff" if measure else "#f0fdfa" if related else "#ffffff"
            svg.append(f'<g><title>{escape(full_name)} · {escape(dtype)}</title><rect x="1" y="{row_y}" width="{CARD_WIDTH-2}" height="{row_h}" fill="{fill}"/><path d="M 1 {row_y + row_h} H {CARD_WIDTH-1}" stroke="#f1f5f9"/>')
            for i, line in enumerate(lines):
                label = ("ƒ " if measure and i == 0 else "") + line
                svg.append(f'<text x="16" y="{row_y + 20 + i*16}" font-size="13" fill="{"#7e22ce" if measure else "#203747"}">{escape(label)}</text>')
            svg.append(f'<text x="{CARD_WIDTH-14}" y="{row_y + 20}" text-anchor="end" font-size="11" fill="#64748b">{escape(dtype)}</text></g>')
        svg.append('</g>')
    svg.extend([f'<text x="{MARGIN}" y="{height-42}" fill="#526879" font-size="13">1 = uno · * = muchos · Flecha = dirección de filtro · Línea discontinua = inactiva · ƒ = medida DAX</text>',
                f'<text x="{MARGIN}" y="{height-19}" fill="#64748b" font-size="12">Cardinalidades y filtros efectivos: propiedades TMDL o predeterminados verificados por el motor.</text>',
                '</g></svg>'])
    return "\n".join(svg)
