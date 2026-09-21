#!/usr/bin/env python3
"""Generate docs/mimic/mongodb_data_dictionary.md from the live MongoDB database.

Every count, percentage, range and value list in the output is measured by a full scan of
each collection at run time. Only the prose descriptions are written by hand. Re-run after
any change to the data:

    python scripts/build_mongo_dictionary.py

Atlas SRV lookups fail through some stub resolvers (systemd-resolved in particular). When
the mongodb+srv URI cannot be parsed, this falls back to resolving the SRV record against
a public resolver and connecting to the seed list directly.
"""
from __future__ import annotations

import datetime
import os
import re
from collections import defaultdict
from pathlib import Path

from bson import ObjectId
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "mimic" / "mongodb_data_dictionary.md"
DB_NAME = os.environ.get("MONGODB_DB", "neuroshield")
DISTINCT_CAP = 80
PUBLIC_RESOLVERS = ["8.8.8.8", "1.1.1.1"]


# --------------------------------------------------------------------------- connection
def load_env() -> None:
    env = ROOT / ".env"
    if not env.is_file():
        return
    for line in env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def connect() -> MongoClient:
    load_env()
    uri = os.environ.get("MONGO_URI") or os.environ.get("MONGODB_URI")
    if not uri:
        raise SystemExit("set MONGO_URI (or MONGODB_URI), or put it in .env")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=20000)
        client.server_info()
        return client
    except Exception as exc:                                   # noqa: BLE001 - any failure falls back
        m = re.match(r"mongodb\+srv://([^:]+):([^@]+)@([^/?]+)", uri)
        if not m:
            raise
        print(f"srv connection failed ({type(exc).__name__}); resolving seed list via public DNS")
        user, password, host = m.groups()
        import dns.resolver

        r = dns.resolver.Resolver(configure=False)
        r.nameservers = list(PUBLIC_RESOLVERS)
        r.timeout = r.lifetime = 15
        seeds = ",".join(f"{a.target.to_text().rstrip('.')}:{a.port}"
                         for a in r.resolve(f"_mongodb._tcp.{host}", "SRV"))
        direct = (f"mongodb://{user}:{password}@{seeds}"
                  "/?tls=true&authSource=admin&retryWrites=true&w=majority")
        client = MongoClient(direct, serverSelectionTimeoutMS=30000)
        client.server_info()
        return client


# --------------------------------------------------------------------------- profiling
def type_name(v) -> str:
    if v is None:
        return "null"
    for cls, name in ((bool, "bool"), (int, "int"), (float, "float"), (str, "str"),
                      (list, "list"), (dict, "dict"), (ObjectId, "ObjectId")):
        if isinstance(v, cls):
            return name
    if isinstance(v, (datetime.datetime, datetime.date)):
        return "datetime"
    return type(v).__name__


class FieldStats:
    def __init__(self) -> None:
        self.n = 0
        self.types: dict[str, int] = defaultdict(int)
        self.values: dict[str, int] = {}
        self.overflowed = False
        self.lo = self.hi = None
        self.len_lo = self.len_hi = None
        self.item_keys: set[str] = set()

    def add(self, v) -> None:
        self.n += 1
        t = type_name(v)
        self.types[t] += 1
        if t in ("int", "float"):
            self.lo = v if self.lo is None else min(self.lo, v)
            self.hi = v if self.hi is None else max(self.hi, v)
        if t == "list":
            n = len(v)
            self.len_lo = n if self.len_lo is None else min(self.len_lo, n)
            self.len_hi = n if self.len_hi is None else max(self.len_hi, n)
            self.item_keys.update(k for it in v if isinstance(it, dict) for k in it)
        if t in ("str", "int", "float", "bool", "null"):
            key = str(v)[:120]
            if key in self.values:
                self.values[key] += 1
            elif not self.overflowed and len(self.values) < DISTINCT_CAP:
                self.values[key] = 1
            else:
                self.overflowed = True

    @property
    def distinct(self) -> str:
        return f"{DISTINCT_CAP}+" if self.overflowed else str(len(self.values))

    def top(self, k: int) -> list[tuple[str, int]]:
        return sorted(self.values.items(), key=lambda kv: (-kv[1], kv[0]))[:k]


def profile(db) -> dict:
    out = {}
    for name in sorted(db.list_collection_names()):
        col = db[name]
        total = col.count_documents({})
        fields: dict[str, FieldStats] = defaultdict(FieldStats)

        def walk(doc, prefix=""):
            for k, v in doc.items():
                path = prefix + k
                fields[path].add(v)
                if isinstance(v, dict):
                    walk(v, path + ".")

        for doc in col.find({}, batch_size=500):
            walk(doc)
        out[name] = {"count": total, "fields": dict(fields),
                     "indexes": [(i["name"], list(i["key"].items())) for i in col.list_indexes()]}
        print(f"  profiled {name}: {total:,} documents, {len(fields)} field paths")
    return out


# --------------------------------------------------------------------------- rendering
def fmt_num(v) -> str:
    if isinstance(v, float):
        return f"{v:,.6g}"
    return f"{v:,}"


def token(k: str, n: int, n_distinct: int) -> str:
    label = f"`{k}`" if len(k) < 34 else f"`{k[:31]}…`"
    return label + (f" ({n:,})" if n_distinct > 1 else "")


# Never render the values of these fields, however few there are. A truncated hash is still
# credential material, and a data dictionary is exactly the kind of file that gets shared;
# contact addresses are personal data and do not belong in a document either.
REDACTED_FIELDS = {"password_hash", "email"}

# Field paths left out of the rendered dictionary entirely, by collection. The fields still
# exist in the documents and are still profiled — they are simply not published here.
OMITTED_FIELDS = {
    "weekly_monitoring": {"simulated_trajectory", "source", "discharge_baseline.source"},
}


def describe(st: FieldStats, total: int, path: str = "") -> str:
    """Range / values cell, chosen by what the field actually looks like."""
    if path.rsplit(".", 1)[-1] in REDACTED_FIELDS:
        return f"{st.distinct} distinct — **values withheld**"
    bits = []
    if st.lo is not None and st.distinct not in ("1", "2", "3", "4", "5"):
        bits.append(f"{fmt_num(st.lo)} to {fmt_num(st.hi)}")
    if st.len_lo is not None:
        bits.append(f"{st.len_lo} to {st.len_hi} items")
        if st.item_keys:
            bits.append("item keys: " + ", ".join(f"`{k}`" for k in sorted(st.item_keys)))
    if st.overflowed:
        bits.append(f"{st.distinct} distinct")
    elif st.values:
        top = st.top(8)
        if len(top) <= 6:
            bits.append(", ".join(token(k, v, len(st.values)) for k, v in top))
        else:
            bits.append(f"{len(st.values)} distinct; most common "
                        + ", ".join(token(k, v, len(st.values)) for k, v in top[:3]))
    return "; ".join(bits) or "—"


def types_cell(st: FieldStats) -> str:
    order = sorted(st.types.items(), key=lambda kv: -kv[1])
    return " / ".join(t for t, _ in order)


def present_cell(st: FieldStats, total: int) -> str:
    if st.n == total:
        return "all"
    pct = 100.0 * st.n / total if total else 0.0
    return f"{pct:.2f}".rstrip("0").rstrip(".") + "%"


def render(prof: dict, notes: dict, descs: dict, order: list[str]) -> str:
    L: list[str] = []
    total_docs = sum(c["count"] for c in prof.values())
    L.append("# Preventra MongoDB — data dictionary\n")
    L.append(f"Every collection in the `{DB_NAME}` database, measured by a full scan. "
             f"**{len(prof)} collections · {total_docs:,} documents.**\n")
    L.append(f"> Built by `scripts/build_mongo_dictionary.py`. Do not edit by hand — "
             f"re-run it after any change to the data.\n")

    L.append("| Collection | Documents | Field paths | What it holds |")
    L.append("|---|---|---|---|")
    for name in order:
        if name not in prof:
            continue
        c = prof[name]
        L.append(f"| [`{name}`](#{name.replace('_', '-')}) | {c['count']:,} | "
                 f"{len(c['fields'])} | {notes.get(name, {}).get('one_line', '')} |")
    L.append("")

    if "__preamble__" in notes:
        L.append(notes["__preamble__"])

    for name in order:
        if name not in prof:
            continue
        c = prof[name]
        meta = notes.get(name, {})
        L.append(f"\n## {name}\n")
        L.append(meta.get("intro", ""))
        idx = [f"`{{{', '.join(f'{k}: {v}' for k, v in keys)}}}`" for _, keys in c["indexes"]]
        L.append(f"\n**{c['count']:,} documents · {len(c['fields'])} field paths · "
                 f"{len(idx)} index{'es' if len(idx) != 1 else ''}:** " + ", ".join(idx) + "\n")
        L.append("| Field | Type | Present | Range / values | Meaning |")
        L.append("|---|---|---|---|---|")
        omitted = OMITTED_FIELDS.get(name, set())
        for path, st in sorted(c["fields"].items()):
            if path == "_id" or path in omitted:
                continue
            d = descs.get(name, {}).get(path, "")
            L.append(f"| `{path}` | {types_cell(st)} | {present_cell(st, c['count'])} | "
                     f"{describe(st, c['count'], path)} | {d} |")
        if meta.get("after"):
            L.append("\n" + meta["after"])
    return "\n".join(L) + "\n"


def main() -> None:
    from mongo_dictionary_text import COLLECTION_ORDER, NOTES, DESCRIPTIONS  # noqa: PLC0415

    client = connect()
    db = client[DB_NAME]
    print(f"connected to {DB_NAME}")
    prof = profile(db)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(prof, NOTES, DESCRIPTIONS, COLLECTION_ORDER), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
