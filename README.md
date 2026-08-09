# Dynamite Sampler API
API for the dynamite sampler board.

This repo contains a schema which defines the api. It also contains generator scripts that will auto generate files for various languages.

## Layout

- `schema/ble_dsl.py` — the schema DSL framework: the primitive type registry (`uint8`, `int8`, `uint16`, `int24`, `uint32`, ...), payload markers (`Utf8String`, `Bytes`), and the `Service` / `CharacteristicRead/Write/Notify/Indicate` base classes. Shared by every board.
- `schema/dynamite_sampler.py` — the device schema for this board. A new board gets its own module that imports `ble_dsl`.
- `schema/generator.py` — parses a schema module into a resolved, typed model (IR), validates it, and renders one output file per language target.
- `templates/*.j2` — one Jinja2 template per language target. Templates only see resolved type info and precomputed byte offsets.
- `python/` — generated Python API. Do not edit by hand.
- `tests/` — golden-file, model, validation, and known-vector tests.

## Generating

Run from the repo root:

```
python -m schema.generator
```

## Adding a primitive type

Add one `PrimitiveType` instance to the registry in `schema/ble_dsl.py`. Size, signedness, and the struct format code all derive from it; no template or generator changes are needed. Types without a struct format code (e.g. 3-byte ints) automatically fall back to `int.from_bytes` / `int.to_bytes` in generated code.

## Adding a language

Add a template under `templates/` and one `Target` entry in `generator.py` (`TARGETS`). The model is parsed once and rendered once per target.

## Wire conventions

These decisions apply to every generated backend:

- All multi-byte values are **little-endian** (the GATT convention).
- `list[T]` as a struct field means "repeat `T` until the end of the buffer". Such a field must be the last field of the struct, and the struct becomes variable-length.
- Enums are serialized as 1-byte unsigned integers (`EnumDef.width`; parameterized before an enum needs more than 256 values).
- Struct payloads are unpack-only for now: generated pack code for a struct payload raises `NotImplementedError`.

Schema modules must not use `from __future__ import annotations` — the generator reads annotations as live objects.

## Tests

```
python -m unittest discover -s tests
```

The golden-file test fails if the committed `python/dynamite_sampler_api.py` is out of date; regenerate it with the command above.
