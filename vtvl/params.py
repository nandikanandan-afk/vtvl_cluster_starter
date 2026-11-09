"""Parameter database loader with provenance.

Every physical input of the model is read from ``data/parameters_baseline.json``
(the team's verified database) or, for the few labeled assumptions that the
database states only in prose, from ``data/parameters_supplement.json``.

Names are ``"<group>.<key>"`` (e.g. ``"engine.isp_sl"``). A bare ``"<key>"`` is
accepted when it is unique across groups. Physics code asks for values with the
expected units, ``P.v("engine.isp_sl", "s")``; a unit mismatch raises.
Overrides (sweeps, calibration) are applied by name and recorded.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / 'data' / 'parameters_baseline.json'
SUPPLEMENT_PATH = ROOT / 'data' / 'parameters_supplement.json'

# Unit strings that appear in the database. Anything else is rejected so a
# typo or a non-SI entry is caught at load time.
KNOWN_UNITS = {
    'N', 'kg', 'm', 's', 'm/s', 'Pa', '-', 'deg', 'count', 'kg/N', 'kg, N', 'SI',
    'g0', 'g0 (non-gravitational, thrust+drag over mass)',
}


@dataclass
class Parameter:
    """One database entry plus its provenance."""
    name: str
    value: Any
    units: str
    source: str
    source_type: str
    confidence: str
    range: Any = None
    used_for: str = ''
    notes: str = ''
    symbol: str = ''
    origin_file: str = ''
    overridden: bool = False
    baseline_value: Any = None
    override_reason: str = ''


class ParameterError(ValueError):
    pass


def _numeric_range(rng) -> tuple[float, float] | None:
    if isinstance(rng, (list, tuple)) and len(rng) == 2 and all(isinstance(x, (int, float)) for x in rng):
        return float(rng[0]), float(rng[1])
    return None


def _load_file(path: Path, origin: str) -> tuple[dict, dict[str, Parameter]]:
    raw = json.loads(path.read_text(encoding='utf-8'))
    meta = raw.get('meta', {})
    out: dict[str, Parameter] = {}
    for group, entries in raw.items():
        if group == 'meta':
            continue
        for key, e in entries.items():
            name = f'{group}.{key}'
            for req in ('value', 'units', 'source'):
                if req not in e:
                    raise ParameterError(f'{origin}:{name} lacks required field {req!r}')
            out[name] = Parameter(
                name=name, value=e['value'], units=e['units'], source=e['source'],
                source_type=e.get('source_type', ''), confidence=e.get('confidence', ''),
                range=e.get('range'), used_for=e.get('used_for', ''), notes=e.get('notes', ''),
                symbol=e.get('symbol', ''), origin_file=origin, baseline_value=copy.deepcopy(e['value']),
            )
    return meta, out


class ParameterSet:
    """Resolved, validated parameter set. Immutable by convention: use ``with_overrides``."""

    def __init__(self, params: dict[str, Parameter], meta: dict):
        self._p = params
        self.meta = meta
        self._short: dict[str, list[str]] = {}
        for name in params:
            self._short.setdefault(name.split('.', 1)[1], []).append(name)
        self.validate()

    # ---- lookup -----------------------------------------------------------------
    def resolve(self, name: str) -> str:
        if name in self._p:
            return name
        hits = self._short.get(name, [])
        if len(hits) == 1:
            return hits[0]
        if not hits:
            raise KeyError(f'Unknown parameter {name!r}')
        raise KeyError(f'Ambiguous parameter {name!r}: use one of {hits}')

    def get(self, name: str) -> Parameter:
        return self._p[self.resolve(name)]

    def v(self, name: str, units: str | None = None):
        """Return the value; if ``units`` is given it must match the database units."""
        p = self.get(name)
        if units is not None and p.units != units:
            raise ParameterError(f'{p.name}: code expects units {units!r}, database has {p.units!r}')
        if p.value is None:
            raise ParameterError(f'{p.name} has no value (it must be calibrated or overridden first)')
        return p.value

    def names(self) -> list[str]:
        return list(self._p)

    # ---- validation ---------------------------------------------------------------
    def validate(self) -> None:
        for p in self._p.values():
            if p.units not in KNOWN_UNITS:
                raise ParameterError(f'{p.name}: unrecognised units {p.units!r}')
            rng = _numeric_range(p.range)
            if rng and isinstance(p.value, (int, float)) and not isinstance(p.value, bool):
                lo, hi = rng
                if not (lo - 1e-12 <= p.value <= hi + 1e-12) and not p.override_reason.startswith('out-of-range allowed'):
                    raise ParameterError(f'{p.name}={p.value} outside its range [{lo}, {hi}]')
            if isinstance(p.value, (int, float)) and not isinstance(p.value, bool):
                if p.value != p.value:  # NaN
                    raise ParameterError(f'{p.name} is NaN')

    # ---- overrides ----------------------------------------------------------------
    def with_overrides(self, overrides: dict[str, Any] | None, reason: str = 'override',
                       allow_out_of_range: bool = False) -> 'ParameterSet':
        """Return a copy with values replaced by name. Out-of-range values raise unless allowed."""
        new = {k: copy.deepcopy(p) for k, p in self._p.items()}
        for name, value in (overrides or {}).items():
            full = self.resolve(name)
            p = new[full]
            if isinstance(p.value, dict) and isinstance(value, dict):
                merged = copy.deepcopy(p.value)
                merged.update(value)
                value = merged
            p.value = value
            p.overridden = True
            p.override_reason = ('out-of-range allowed: ' if allow_out_of_range else '') + reason
        return ParameterSet(new, self.meta)

    # ---- provenance output ----------------------------------------------------------
    def records(self) -> list[dict]:
        rows = []
        for p in self._p.values():
            d = asdict(p)
            d['source_description'] = self.source_description(p.source)
            rows.append(d)
        return rows

    def source_description(self, source: str) -> str:
        sources = self.meta.get('sources', {})
        found = [f'{code}: {sources[code]}' for code in sources if code in source.replace(',', ' ').replace('/', ' ').split()]
        return ' | '.join(found)

    def write(self, path: Path) -> None:
        path.write_text(json.dumps({'meta': self.meta, 'parameters': self.records()}, indent=2, default=str) + '\n',
                        encoding='utf-8')


def load_parameters(baseline: Path = BASELINE_PATH, supplement: Path | None = SUPPLEMENT_PATH) -> ParameterSet:
    meta, params = _load_file(baseline, baseline.name)
    if supplement is not None and supplement.exists():
        smeta, sparams = _load_file(supplement, supplement.name)
        clash = set(params) & set(sparams)
        if clash:
            raise ParameterError(f'Supplement redefines database entries: {sorted(clash)}')
        params.update(sparams)
        meta = dict(meta)
        meta['supplement'] = smeta
    return ParameterSet(params, meta)
