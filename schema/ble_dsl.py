"""Framework for declaring BLE GATT schemas.

A device schema module (see dynamite_sampler.py) imports this module and
declares enums, payload structs, services, and characteristics. The
generator (generator.py) parses a schema module into a resolved model and
renders one language-specific API file per target.

Wire conventions (shared by every generated language backend):
  * All multi-byte values are little-endian (the GATT convention).
  * ``list[T]`` as a struct field means "repeat T until the end of the
    buffer"; such a field must be the last field of the struct.
  * Enums are serialized as unsigned integers of ``EnumDef.width`` bytes
    (1 byte today).
  * Struct payloads are unpack-only: generated pack code for a struct
    payload raises NotImplementedError.

WARNING: schema modules must NOT use ``from __future__ import annotations``.
The generator reads annotations as live objects (primitive instances, enum
and struct classes); string annotations would break parsing.
"""

import dataclasses
import enum
from typing import Generic, TypeVar

# struct format codes per integer size, indexed (unsigned, signed).
# Sizes without an entry (e.g. 3-byte ints) have no struct code and fall
# back to int.from_bytes / int.to_bytes in generated code.
_STRUCT_CODES = {1: ("B", "b"), 2: ("H", "h"), 4: ("I", "i")}


def struct_code_for(size: int, signed: bool) -> str | None:
    """Return the struct format code for a `size`-byte integer, or None."""
    codes = _STRUCT_CODES.get(size)
    return codes[signed] if codes else None


@dataclasses.dataclass(frozen=True)
class PrimitiveType:
    """A primitive integer type usable as a struct field or payload.

    Instances are used directly as dataclass annotations in schema modules,
    so ``dataclasses.fields()`` hands the generator the full metadata
    (name, size, signedness) without any separate lookup table. Type
    checkers do not understand this; it is intentional.
    """

    name: str
    size: int  # bytes
    signed: bool = False

    @property
    def struct_code(self) -> str | None:
        return struct_code_for(self.size, self.signed)


# The single registry of primitive types. Adding a type here (and exporting
# it) is all that is needed; sizes, signedness, and struct codes derive.
uint8 = PrimitiveType("uint8", 1)
int8 = PrimitiveType("int8", 1, signed=True)
uint16 = PrimitiveType("uint16", 2)
int24 = PrimitiveType("int24", 3, signed=True)
uint32 = PrimitiveType("uint32", 4)


class Utf8String:
    """Marker for a variable-length UTF-8 string payload."""


class Bytes:
    """Marker for a variable-length raw-bytes payload."""


T = TypeVar("T")


class CharacteristicRead(Generic[T]):
    pass


class CharacteristicWrite(Generic[T]):
    pass


class CharacteristicNotify(Generic[T]):
    pass


class CharacteristicIndicate(Generic[T]):
    pass


class Service:
    UUID: str
    advertised: bool = False
