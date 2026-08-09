import inspect
import enum
import typing
import dataclasses
import black
from jinja2 import Environment, FileSystemLoader

# Import your schema
import schema


def get_base_type_name(t):
    """Helper to extract type names, including from lists."""
    origin = typing.get_origin(t)
    if origin is list:
        args = typing.get_args(t)
        return {"is_list": True, "type": args[0].__name__}
    elif inspect.isclass(t):
        return {"is_list": False, "type": t.__name__}
    return {"is_list": False, "type": str(t)}


def parse_schema():
    api_model = {"enums": [], "structs": [], "services": []}

    # 1. Parse Enums
    for name, obj in inspect.getmembers(schema, inspect.isclass):
        if issubclass(obj, enum.IntEnum) and obj is not enum.IntEnum:
            api_model["enums"].append(
                {
                    "name": name,
                    "docstring": inspect.getdoc(obj),
                    "members": {e.name: e.value for e in obj},
                }
            )

    # 2. Parse Dataclasses (Structs)
    for name, obj in inspect.getmembers(schema, inspect.isclass):
        if dataclasses.is_dataclass(obj):
            fields = []
            for f in dataclasses.fields(obj):
                type_info = get_base_type_name(f.type)
                fields.append(
                    {
                        "name": f.name,
                        "type": type_info["type"],
                        "is_list": type_info["is_list"],
                    }
                )
            api_model["structs"].append(
                {
                    "name": name,
                    "docstring": inspect.getdoc(obj),
                    "fields": fields,
                }
            )

    # 3. Parse Services and Characteristics
    for name, obj in inspect.getmembers(schema, inspect.isclass):
        if issubclass(obj, schema.Service) and obj is not schema.Service:
            service_data = {
                "name": name,
                "docstring": inspect.getdoc(obj),
                "uuid": getattr(obj, "UUID", ""),
                "advertised": getattr(obj, "advertised", False),
                "characteristics": [],
            }

            # Find characteristics inside the service
            for char_name, char_obj in inspect.getmembers(obj, inspect.isclass):
                if char_name.startswith("__"):
                    continue

                char_data = {
                    "name": char_name,
                    "docstring": inspect.getdoc(char_obj),
                    "uuid": getattr(char_obj, "UUID", ""),
                    "props": [],
                }

                # Look at base classes to see if it's Read, Write, Notify
                if hasattr(char_obj, "__orig_bases__"):
                    for base in char_obj.__orig_bases__:
                        base_origin = typing.get_origin(base) or base
                        base_name = getattr(base_origin, "__name__", "")

                        if base_name in [
                            "CharacteristicRead",
                            "CharacteristicWrite",
                            "CharacteristicNotify",
                            "CharacteristicIndicate",
                        ]:
                            prop_type = base_name.replace("Characteristic", "").lower()
                            # Get the generic type argument (e.g., the payload type)
                            args = typing.get_args(base)
                            payload_type = args[0].__name__ if args else "Bytes"

                            char_data["props"].append(
                                {"type": prop_type, "payload": payload_type}
                            )

                if char_data["props"]:
                    service_data["characteristics"].append(char_data)

            api_model["services"].append(service_data)

    return api_model


if __name__ == "__main__":
    model = parse_schema()

    # Render Python Template
    env = Environment(
        loader=FileSystemLoader("templates"), trim_blocks=True, lstrip_blocks=True
    )
    template = env.get_template("python.j2")
    output = template.render(model)

    # Format output using Black
    try:
        output = black.format_str(output, mode=black.Mode())
    except Exception as e:
        print(f"Warning: Code formatting with Black failed: {e}")

    with open("python/dynamite_sampler_api.py", "w") as f:
        f.write(output)

    print("Successfully generated dynamite_sampler_api.py")
