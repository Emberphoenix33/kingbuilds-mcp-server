"""Data transformation tool: convert between JSON and CSV, and run simple
aggregations (sum/average/min/max/count/unique) over a field.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
from typing import Any

from mcp.server.fastmcp import FastMCP

from mcp_server.config import Settings

logger = logging.getLogger("mcp_server.tools.transform")

_INT_RE = re.compile(r"^[+-]?\d+$")
_FLOAT_RE = re.compile(r"^[+-]?(\d+\.\d*|\.\d+|\d+)([eE][+-]?\d+)?$")

_AGGREGATE_OPS = {"sum", "average", "min", "max", "count", "unique"}


def _coerce_scalar(value: str) -> Any:
    """Best-effort coercion of a CSV cell to int/float, leaving text as-is."""
    if value == "":
        return None
    if _INT_RE.match(value):
        return int(value)
    if _FLOAT_RE.match(value):
        return float(value)
    return value


def _parse_input(data: str, input_format: str) -> Any:
    if input_format == "json":
        try:
            return json.loads(data)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON input: {exc}") from exc
    if input_format == "csv":
        reader = csv.DictReader(io.StringIO(data))
        return [{key: _coerce_scalar(value) for key, value in row.items()} for row in reader]
    raise ValueError(f"Unsupported input_format: {input_format!r} (expected 'json' or 'csv')")


def _records_to_csv(records: list[Any]) -> str:
    if not records:
        return ""
    if not all(isinstance(r, dict) for r in records):
        raise ValueError("Converting to CSV requires a JSON array of objects")

    fieldnames: list[str] = []
    for record in records:
        for key in record:
            if key not in fieldnames:
                fieldnames.append(key)

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue()


def _extract_values(parsed: Any, field: str | None) -> list[Any]:
    if not isinstance(parsed, list):
        raise ValueError("This operation requires the data to be a JSON array or CSV rows")
    values: list[Any] = []
    for item in parsed:
        if isinstance(item, dict):
            if field is None:
                raise ValueError("`field` is required when the data is a list of objects/rows")
            values.append(item.get(field))
        else:
            values.append(item)
    return values


def _numeric(values: list[Any]) -> list[float]:
    numeric: list[float] = []
    for value in values:
        if value is None or value == "":
            continue
        numeric.append(float(value))
    return numeric


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.tool(
        name="transform_data",
        description=(
            "Transform or aggregate tabular/record data. operation='convert' converts between "
            "JSON (array of objects) and CSV (requires output_format). operation in "
            "{sum, average, min, max, count, unique} aggregates a single `field` across the "
            "records (omit `field` if `data` is a flat JSON array of numbers)."
        ),
    )
    def transform_data(
        data: str,
        input_format: str,
        operation: str,
        output_format: str | None = None,
        field: str | None = None,
    ) -> dict[str, Any]:
        try:
            parsed = _parse_input(data, input_format)
        except ValueError as exc:
            return {"error": str(exc)}

        try:
            if operation == "convert":
                return _do_convert(parsed, input_format, output_format)
            if operation in _AGGREGATE_OPS:
                return _do_aggregate(parsed, operation, field)
            return {"error": f"Unsupported operation: {operation!r}"}
        except ValueError as exc:
            return {"error": str(exc)}


def _do_convert(parsed: Any, input_format: str, output_format: str | None) -> dict[str, Any]:
    if not output_format:
        raise ValueError("output_format is required for operation='convert'")
    if output_format == input_format:
        raise ValueError("output_format must differ from input_format")

    if output_format == "csv":
        result = _records_to_csv(parsed)
    elif output_format == "json":
        result = json.dumps(parsed, indent=2)
    else:
        raise ValueError(f"Unsupported output_format: {output_format!r} (expected 'json' or 'csv')")

    logger.info("transform_data: convert %s -> %s", input_format, output_format)
    return {"operation": "convert", "output_format": output_format, "result": result}


def _do_aggregate(parsed: Any, operation: str, field: str | None) -> dict[str, Any]:
    values = _extract_values(parsed, field)

    if operation == "count":
        result: Any = sum(1 for v in values if v is not None and v != "")
    elif operation == "unique":
        seen: list[Any] = []
        for value in values:
            if value not in seen:
                seen.append(value)
        result = seen
    else:
        numeric = _numeric(values)
        if not numeric:
            raise ValueError("No numeric values found to aggregate")
        if operation == "sum":
            result = sum(numeric)
        elif operation == "average":
            result = sum(numeric) / len(numeric)
        elif operation == "min":
            result = min(numeric)
        else:  # max
            result = max(numeric)

    logger.info("transform_data: %s(field=%s) -> %r", operation, field, result)
    return {"operation": operation, "field": field, "result": result, "count": len(values)}
