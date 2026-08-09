"""Generates language-specific API files from a BLE schema module.

The pipeline is: parse a schema module into a resolved, typed IR (Model),
validate it, then render one template per language target. Templates only
ever see resolved type information (TypeRef) and precomputed byte offsets,
so they contain no type-name dispatch and adding a language is "new
template + one Target entry".

Usage (from the repo root):
    python -m schema.generator
"""

import dataclasses
import enum
import inspect
import pathlib
import typing

import black
from jinja2 import Environment, FileSystemLoader

from schema import ble_dsl, dynamite_sampler

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent


class SchemaError(Exception):
    """Raised when a schema module is invalid or unsupported."""


# ---------------------------------------------------------------------------
# IR: the stable contract between the generator and every language template.
# ---------------------------------------------------------------------------


class TypeKind(str, enum.Enum):
    PRIMITIVE = "primitive"
    ENUM = "enum"
    STRUCT = "struct"
    STRING = "string"
    BYTES = "bytes"


@dataclasses.dataclass(frozen=True)
class TypeRef:
    """A fully resolved type reference.

    size is the wire size in bytes, or None for variable-length types
    (Utf8String, Bytes, and structs containing a list). struct_code is the
    language-agnostic integer encoding hint derived from size + signedness;
    it is None when no fixed-width encoding exists (e.g. 3-byte ints).
    """

    kind: TypeKind
    name: str
    size: int | None = None
    signed: bool = False
    struct_code: str | None = None


@dataclasses.dataclass
class FieldDef:
    name: str
    type: TypeRef  # element type (list element type when is_list)
    offset: int  # absolute byte offset within the struct
    is_list: bool = False  # True: repeats until end of buffer (last field)


@dataclasses.dataclass
class StructDef:
    name: str
    docstring: str | None
    fields: list[FieldDef] = dataclasses.field(default_factory=list)
    size: int | None = None  # None for variable-length structs


@dataclasses.dataclass
class EnumDef:
    name: str
    docstring: str | None
    members: dict[str, int]
    width: int = 1  # wire width in bytes


@dataclasses.dataclass
class CharacteristicDef:
    name: str
    docstring: str | None
    uuid: str
    props: list[str]
    read_payload: TypeRef | None = None
    write_payload: TypeRef | None = None


@dataclasses.dataclass
class ServiceDef:
    name: str
    docstring: str | None
    uuid: str
    advertised: bool
    characteristics: list[CharacteristicDef]


@dataclasses.dataclass
class Model:
    enums: list[EnumDef]
    structs: list[StructDef]
    services: list[ServiceDef]


# ---------------------------------------------------------------------------
# Parsing: schema module -> resolved Model
# ---------------------------------------------------------------------------

# Characteristic base classes mapped to the GATT property they provide.
CHARACTERISTIC_PROPS = {
    ble_dsl.CharacteristicRead: "read",
    ble_dsl.CharacteristicWrite: "write",
    ble_dsl.CharacteristicNotify: "notify",
    ble_dsl.CharacteristicIndicate: "indicate",
}

# Properties whose payload is received from the device and unpacked.
INBOUND_PROPS = {"read", "notify", "indicate"}


@dataclasses.dataclass
class _Context:
    module: object
    enums_by_class: dict[type, EnumDef]
    structs_by_class: dict[type, StructDef]
    resolved_sizes: dict[type, int | None] = dataclasses.field(default_factory=dict)
    in_progress: set[type] = dataclasses.field(default_factory=set)


def get_docstring(obj):
    """Return the docstring defined on obj itself, ignoring inherited ones.

    inspect.getdoc() walks the MRO, which would pick up docstrings from base
    classes such as typing.Generic for classes that define no docstring.
    """
    doc = obj.__dict__.get("__doc__")
    return inspect.cleandoc(doc) if doc else None


def require_uuid(obj, what):
    uuid = getattr(obj, "UUID", None)
    if not isinstance(uuid, str) or not uuid:
        raise SchemaError(f"{what} must define a non-empty string UUID attribute")
    return uuid


def resolve_type(annotation, where, ctx) -> TypeRef:
    """Resolve one schema annotation to a TypeRef, or raise SchemaError.

    Annotations are live objects (primitive instances, enum/struct classes),
    so this is an identity/instance dispatch, not a name lookup.
    """
    if isinstance(annotation, str):
        raise SchemaError(
            f"'{where}': annotation {annotation!r} is a string; schema modules "
            "must not use 'from __future__ import annotations'"
        )
    if isinstance(annotation, ble_dsl.PrimitiveType):
        return TypeRef(
            kind=TypeKind.PRIMITIVE,
            name=annotation.name,
            size=annotation.size,
            signed=annotation.signed,
            struct_code=annotation.struct_code,
        )
    if annotation is ble_dsl.Utf8String:
        return TypeRef(kind=TypeKind.STRING, name="Utf8String")
    if annotation is ble_dsl.Bytes:
        return TypeRef(kind=TypeKind.BYTES, name="Bytes")
    if annotation in ctx.enums_by_class:
        enum_def = ctx.enums_by_class[annotation]
        return TypeRef(
            kind=TypeKind.ENUM,
            name=enum_def.name,
            size=enum_def.width,
            struct_code=ble_dsl.struct_code_for(enum_def.width, signed=False),
        )
    if annotation in ctx.structs_by_class:
        struct_def = ctx.structs_by_class[annotation]
        return TypeRef(
            kind=TypeKind.STRUCT,
            name=struct_def.name,
            size=resolve_struct(annotation, struct_def, ctx),
        )
    raise SchemaError(
        f"'{where}': unsupported type {annotation!r}. Use ble_dsl primitives, "
        "IntEnums, schema structs, Utf8String, Bytes, or list[...] of those."
    )


def resolve_struct(cls, struct_def, ctx) -> int | None:
    """Resolve struct_def's fields (with byte offsets); return its wire size.

    Returns None for variable-length structs (those ending in a list field).
    """
    if cls in ctx.resolved_sizes:
        return ctx.resolved_sizes[cls]
    if cls in ctx.in_progress:
        raise SchemaError(f"Struct '{struct_def.name}' is recursively defined")
    ctx.in_progress.add(cls)

    offset = 0
    raw_fields = dataclasses.fields(cls)
    for index, field in enumerate(raw_fields):
        where = f"{struct_def.name}.{field.name}"
        annotation = field.type
        if typing.get_origin(annotation) is list:
            args = typing.get_args(annotation)
            if len(args) != 1:
                raise SchemaError(f"'{where}': list fields need exactly one type argument")
            if index != len(raw_fields) - 1:
                raise SchemaError(
                    f"'{where}': list fields repeat to the end of the buffer "
                    "and must be the last field of the struct"
                )
            type_ref = resolve_type(args[0], where, ctx)
            if type_ref.size is None:
                raise SchemaError(f"'{where}': list elements must have a fixed size")
            struct_def.fields.append(FieldDef(field.name, type_ref, offset, is_list=True))
        else:
            type_ref = resolve_type(annotation, where, ctx)
            if type_ref.size is None:
                raise SchemaError(
                    f"'{where}': variable-length type '{type_ref.name}' is only "
                    "allowed as a characteristic payload, not a struct field"
                )
            struct_def.fields.append(FieldDef(field.name, type_ref, offset))
            offset += type_ref.size

    size = None if any(f.is_list for f in struct_def.fields) else offset
    struct_def.size = size
    ctx.resolved_sizes[cls] = size
    ctx.in_progress.discard(cls)
    return size


def parse_characteristic(name, obj, ctx):
    """Parse a characteristic class, or return None if it isn't one."""
    props = []
    read_payload = None
    write_payload = None
    # __orig_bases__ carries subscripted generics (with payload args). Also
    # scan __bases__ so a bare, payload-less CharacteristicRead (a DSL
    # mistake) is caught instead of silently skipped.
    bases = list(getattr(obj, "__orig_bases__", ()))
    for base in obj.__bases__:
        origin = typing.get_origin(base) or base
        if origin in CHARACTERISTIC_PROPS and not any((typing.get_origin(b) or b) is origin for b in bases):
            bases.append(base)
    for base in bases:
        prop = CHARACTERISTIC_PROPS.get(typing.get_origin(base) or base)
        if prop is None:
            continue
        props.append(prop)
        args = typing.get_args(base)
        if not args:
            raise SchemaError(f"Characteristic '{name}': {base!r} is missing its payload type argument")
        payload = resolve_type(args[0], f"characteristic '{name}'", ctx)
        if prop in INBOUND_PROPS:
            read_payload = payload
        else:
            write_payload = payload

    if not props:
        return None

    return CharacteristicDef(
        name=name,
        docstring=get_docstring(obj),
        uuid=require_uuid(obj, f"characteristic '{name}'"),
        props=props,
        read_payload=read_payload,
        write_payload=write_payload,
    )


def parse_service(name, obj, ctx):
    characteristics = []
    # vars() preserves declaration order (inspect.getmembers sorts by name).
    for char_name, char_obj in vars(obj).items():
        if not inspect.isclass(char_obj) or char_obj.__module__ != ctx.module.__name__:
            continue
        char_def = parse_characteristic(char_name, char_obj, ctx)
        if char_def is not None:
            characteristics.append(char_def)

    return ServiceDef(
        name=name,
        docstring=get_docstring(obj),
        uuid=require_uuid(obj, f"service '{name}'"),
        advertised=getattr(obj, "advertised", False),
        characteristics=characteristics,
    )


def parse_schema(module) -> Model:
    """Parse the BLE schema declared in `module` into a resolved Model.

    Only classes defined in `module` itself are collected (the __module__
    filter skips everything imported from ble_dsl or elsewhere), in
    declaration order.
    """
    ctx = _Context(module=module, enums_by_class={}, structs_by_class={})
    enums: list[EnumDef] = []
    structs: list[StructDef] = []
    struct_classes: list[tuple[type, StructDef]] = []
    service_classes: list[tuple[str, type]] = []

    # First pass: register enums and structs so references resolve
    # regardless of where services appear in the module.
    for name, obj in vars(module).items():
        if not inspect.isclass(obj) or obj.__module__ != module.__name__:
            continue
        if issubclass(obj, enum.IntEnum):
            enum_def = EnumDef(name, get_docstring(obj), {m.name: m.value for m in obj})
            enums.append(enum_def)
            ctx.enums_by_class[obj] = enum_def
        elif dataclasses.is_dataclass(obj):
            struct_def = StructDef(name, get_docstring(obj))
            structs.append(struct_def)
            ctx.structs_by_class[obj] = struct_def
            struct_classes.append((obj, struct_def))
        elif issubclass(obj, ble_dsl.Service):
            service_classes.append((name, obj))

    for cls, struct_def in struct_classes:
        resolve_struct(cls, struct_def, ctx)

    services = [parse_service(name, obj, ctx) for name, obj in service_classes]
    return Model(enums=enums, structs=structs, services=services)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate(model: Model) -> None:
    """Cross-cutting schema checks that span multiple definitions."""
    uuid_owners: dict[str, str] = {}

    def check_uuid(uuid, owner):
        key = uuid.casefold()
        if key in uuid_owners:
            raise SchemaError(f"Duplicate UUID '{uuid}' used by {uuid_owners[key]} and {owner}")
        uuid_owners[key] = owner

    for enum_def in model.enums:
        limit = 256**enum_def.width
        for member, value in enum_def.members.items():
            if not 0 <= value < limit:
                raise SchemaError(
                    f"Enum '{enum_def.name}' member {member} = {value} does not "
                    f"fit in {enum_def.width} byte(s)"
                )

    for service in model.services:
        check_uuid(service.uuid, f"service '{service.name}'")
        for char in service.characteristics:
            check_uuid(char.uuid, f"characteristic '{service.name}.{char.name}'")


# ---------------------------------------------------------------------------
# Targets: one template + output path + formatter per language
# ---------------------------------------------------------------------------


def format_python(code: str) -> str:
    return black.format_str(code, mode=black.Mode())


@dataclasses.dataclass(frozen=True)
class Target:
    name: str
    template: str
    out: pathlib.Path
    fmt: typing.Callable[[str], str] | None = None


TARGETS = [
    Target("python", "python.j2", pathlib.Path("python") / "dynamite_sampler_api.py", format_python),
]


def generate(model: Model, targets: list[Target] = TARGETS) -> None:
    """Render every target once from the already-parsed model."""
    env = Environment(
        loader=FileSystemLoader(ROOT_DIR / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    for target in targets:
        output = env.get_template(target.template).render(
            enums=model.enums, structs=model.structs, services=model.services
        )
        if target.fmt is not None:
            # Fail loudly: unformatted output from a broken template is
            # almost certainly broken code.
            output = target.fmt(output)
        out_path = ROOT_DIR / target.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Generated {out_path} ({target.name})")


def main() -> None:
    model = parse_schema(dynamite_sampler)
    validate(model)
    generate(model)


if __name__ == "__main__":
    main()
