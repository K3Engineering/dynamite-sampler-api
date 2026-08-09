"""Generates language-specific API files from the BLE schema."""

import dataclasses
import enum
import inspect
import pathlib
import typing

import black
from jinja2 import Environment, FileSystemLoader

import schema

# Characteristic base classes mapped to the GATT property they provide.
CHARACTERISTIC_PROPS = {
    schema.CharacteristicRead: "read",
    schema.CharacteristicWrite: "write",
    schema.CharacteristicNotify: "notify",
    schema.CharacteristicIndicate: "indicate",
}

# Properties whose payload is received from the device and unpacked.
INBOUND_PROPS = {"read", "notify", "indicate"}

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent


def get_docstring(obj):
    """Return the docstring defined on obj itself, ignoring inherited ones.

    inspect.getdoc() walks the MRO, which would pick up docstrings from base
    classes such as typing.Generic for classes that define no docstring.
    """
    doc = obj.__dict__.get("__doc__")
    return inspect.cleandoc(doc) if doc else None


def get_base_type_name(t):
    """Helper to extract type names, including from lists."""
    if typing.get_origin(t) is list:
        return {"is_list": True, "type": typing.get_args(t)[0].__name__}
    if inspect.isclass(t):
        return {"is_list": False, "type": t.__name__}
    return {"is_list": False, "type": str(t)}


def parse_enum(name, obj):
    return {
        "name": name,
        "docstring": get_docstring(obj),
        "members": {member.name: member.value for member in obj},
    }


def parse_struct(name, obj):
    fields = [
        {"name": field.name, **get_base_type_name(field.type)}
        for field in dataclasses.fields(obj)
    ]
    return {"name": name, "docstring": get_docstring(obj), "fields": fields}


def parse_characteristic(name, obj):
    """Parse a characteristic class, or return None if it isn't one."""
    props = []
    read_payload = None
    write_payload = None
    for base in getattr(obj, "__orig_bases__", ()):
        prop = CHARACTERISTIC_PROPS.get(typing.get_origin(base) or base)
        if prop is None:
            continue
        props.append(prop)
        args = typing.get_args(base)
        payload = args[0].__name__ if args else "Bytes"
        if prop in INBOUND_PROPS:
            read_payload = payload
        else:
            write_payload = payload

    if not props:
        return None

    return {
        "name": name,
        "docstring": get_docstring(obj),
        "uuid": getattr(obj, "UUID", ""),
        "props": props,
        "read_payload": read_payload,
        "write_payload": write_payload,
    }


def parse_service(name, obj):
    characteristics = []
    for char_name, char_obj in inspect.getmembers(obj, inspect.isclass):
        char_data = parse_characteristic(char_name, char_obj)
        if char_data:
            characteristics.append(char_data)

    return {
        "name": name,
        "docstring": get_docstring(obj),
        "uuid": getattr(obj, "UUID", ""),
        "advertised": getattr(obj, "advertised", False),
        "characteristics": characteristics,
    }


def parse_schema():
    model = {"enums": [], "structs": [], "services": []}
    for name, obj in inspect.getmembers(schema, inspect.isclass):
        # Skip classes imported into the schema module from elsewhere.
        if obj.__module__ != schema.__name__:
            continue
        if issubclass(obj, enum.IntEnum):
            model["enums"].append(parse_enum(name, obj))
        elif dataclasses.is_dataclass(obj):
            model["structs"].append(parse_struct(name, obj))
        elif issubclass(obj, schema.Service) and obj is not schema.Service:
            model["services"].append(parse_service(name, obj))
    return model


def generate_python(model):
    env = Environment(
        loader=FileSystemLoader(ROOT_DIR / "templates"),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    output = env.get_template("python.j2").render(model)

    try:
        output = black.format_str(output, mode=black.Mode())
    except Exception as e:
        print(f"Warning: Code formatting with Black failed: {e}")

    out_path = ROOT_DIR / "python" / "dynamite_sampler_api.py"
    out_path.write_text(output, encoding="utf-8")
    print(f"Successfully generated {out_path}")


if __name__ == "__main__":
    generate_python(parse_schema())
