"""Tests for the schema generator: golden output, model shape, validation."""

import dataclasses
import enum
import inspect
import pathlib
import sys
import tempfile
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from schema import ble_dsl, dynamite_sampler, generator  # noqa: E402


class GoldenOutputTest(unittest.TestCase):
    """The committed Python API must match what the generator produces."""

    def test_generated_output_matches_committed_file(self):
        model = generator.parse_schema(dynamite_sampler)
        generator.validate(model)
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp) / "dynamite_sampler_api.py"
            target = dataclasses.replace(generator.TARGETS[0], out=out)
            generator.generate(model, targets=[target])
            generated = out.read_text(encoding="utf-8")
        committed = (generator.ROOT_DIR / "python" / "dynamite_sampler_api.py").read_text(encoding="utf-8")
        self.assertEqual(generated, committed)


class ModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = generator.parse_schema(dynamite_sampler)
        cls.structs = {s.name: s for s in cls.model.structs}

    def test_struct_sizes(self):
        self.assertEqual(self.structs["ADCConfigData"].size, 11)
        self.assertEqual(self.structs["FeedHeader"].size, 2)
        self.assertEqual(self.structs["FeedData"].size, 12)
        self.assertIsNone(self.structs["FeedPacket"].size)  # variable length

    def test_field_offsets(self):
        fields = {f.name: f for f in self.structs["ADCConfigData"].fields}
        self.assertEqual(
            {name: f.offset for name, f in fields.items()},
            {"version": 0, "id": 1, "status": 3, "mode": 5, "clock": 7, "pga": 9},
        )
        samples = next(f for f in self.structs["FeedPacket"].fields if f.name == "samples")
        self.assertTrue(samples.is_list)
        self.assertEqual(samples.offset, 2)
        self.assertEqual(samples.type.size, 12)

    def test_declaration_order_is_preserved(self):
        self.assertEqual(
            [s.name for s in self.model.services],
            ["DynamiteSampler", "OTA", "TxPower", "DeviceInfo"],
        )
        device_info = self.model.services[3]
        self.assertEqual(
            [c.name for c in device_info.characteristics],
            ["ManufacturerName", "FirmwareRevision", "HardwareRevision", "TxPowerLevel"],
        )

    def test_primitive_metadata_is_resolved(self):
        version = self.structs["ADCConfigData"].fields[0]
        self.assertEqual(version.type.kind, generator.TypeKind.PRIMITIVE)
        self.assertEqual(version.type.struct_code, "B")
        ch0 = self.structs["FeedData"].fields[0]
        self.assertIsNone(ch0.type.struct_code)  # int24: no struct code
        self.assertTrue(ch0.type.signed)


class ValidationTest(unittest.TestCase):
    """Bad schemas must fail loudly with clear errors."""

    def parse(self, **namespace):
        module = types.ModuleType("fake_schema")
        module.__dict__.update(namespace)

        def claim(cls):
            # Only re-home classes defined in this test module; skip
            # inherited/builtin classes like int that are immutable.
            if inspect.isclass(cls) and cls.__module__ == __name__:
                cls.__module__ = "fake_schema"
                for attr in vars(cls).values():
                    if inspect.isclass(attr) and attr.__module__ == __name__:
                        attr.__module__ = "fake_schema"

        for value in namespace.values():
            claim(value)
        return generator.parse_schema(module)

    def test_unknown_field_type_raises(self):
        @dataclasses.dataclass
        class Bad:
            x: float

        with self.assertRaisesRegex(generator.SchemaError, "unsupported type"):
            self.parse(Bad=Bad)

    def test_string_annotation_raises(self):
        @dataclasses.dataclass
        class Bad:
            x: "uint8"  # noqa: F821 - deliberately a string annotation

        with self.assertRaisesRegex(generator.SchemaError, "from __future__"):
            self.parse(Bad=Bad)

    def test_duplicate_uuids_raise(self):
        class A(ble_dsl.Service):
            UUID = "1111"

        class B(ble_dsl.Service):
            UUID = "1111"

        model = self.parse(A=A, B=B)
        with self.assertRaisesRegex(generator.SchemaError, "Duplicate UUID"):
            generator.validate(model)

    def test_characteristic_without_payload_argument_raises(self):
        class S(ble_dsl.Service):
            UUID = "1111"

            class C(ble_dsl.CharacteristicRead):
                UUID = "2222"

        with self.assertRaisesRegex(generator.SchemaError, "missing its payload type"):
            self.parse(S=S)

    def test_list_field_must_be_last(self):
        @dataclasses.dataclass
        class Item:
            value: ble_dsl.uint8

        @dataclasses.dataclass
        class Bad:
            items: list[Item]
            tail: ble_dsl.uint8

        with self.assertRaisesRegex(generator.SchemaError, "must be the last field"):
            self.parse(Item=Item, Bad=Bad)

    def test_variable_length_struct_field_raises(self):
        @dataclasses.dataclass
        class Bad:
            name: ble_dsl.Utf8String

        with self.assertRaisesRegex(generator.SchemaError, "variable-length"):
            self.parse(Bad=Bad)

    def test_service_without_uuid_raises(self):
        class S(ble_dsl.Service):
            pass

        with self.assertRaisesRegex(generator.SchemaError, "UUID"):
            self.parse(S=S)

    def test_enum_member_out_of_range_raises(self):
        class Big(enum.IntEnum):
            X = 256

        model = self.parse(Big=Big)
        with self.assertRaisesRegex(generator.SchemaError, "does not fit"):
            generator.validate(model)


if __name__ == "__main__":
    unittest.main()
