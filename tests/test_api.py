"""Known-vector tests for the generated Python API."""

import pathlib
import struct
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "python"))

import dynamite_sampler_api as api  # noqa: E402


def int24(value: int) -> bytes:
    return value.to_bytes(3, byteorder="little", signed=True)


class ADCConfigVectorTest(unittest.TestCase):
    def test_unpack(self):
        data = b"\x01" + struct.pack("<H", 0x1234) + struct.pack("<H", 2) + struct.pack("<H", 3) + struct.pack("<H", 64) + struct.pack("<H", 5)
        cfg = api.DynamiteSampler.ADCConfig.unpack(data)
        self.assertEqual(cfg, api.ADCConfigData(version=1, id=0x1234, status=2, mode=3, clock=64, pga=5))

    def test_unpack_accepts_bytearray(self):
        data = bytearray(b"\x02" + struct.pack("<H", 7) * 5)
        cfg = api.DynamiteSampler.ADCConfig.unpack(data)
        self.assertEqual(cfg.version, 2)
        self.assertEqual(cfg.id, 7)


class FeedPacketVectorTest(unittest.TestCase):
    SAMPLE_0 = int24(1) + int24(-1) + int24(8388607) + int24(-8388608)
    SAMPLE_1 = int24(0) + int24(2) + int24(-2) + int24(100)

    def test_unpack(self):
        packet = struct.pack("<H", 7) + self.SAMPLE_0 + self.SAMPLE_1
        pkt = api.DynamiteSampler.ADCFeed.unpack(packet)
        self.assertEqual(pkt.header.sample_sequence_number, 7)
        self.assertEqual(len(pkt.samples), 2)
        self.assertEqual(pkt.samples[0], api.FeedData(ch0=1, ch1=-1, ch2=8388607, ch3=-8388608))
        self.assertEqual(pkt.samples[1], api.FeedData(ch0=0, ch1=2, ch2=-2, ch3=100))

    def test_partial_trailing_sample_is_zero_padded(self):
        packet = struct.pack("<H", 0) + self.SAMPLE_0 + b"\x01\x02"
        pkt = api.DynamiteSampler.ADCFeed.unpack(packet)
        self.assertEqual(len(pkt.samples), 2)
        self.assertEqual(pkt.samples[1], api.FeedData(ch0=0x0201, ch1=0, ch2=0, ch3=0))

    def test_unpack_empty_payload(self):
        pkt = api.DynamiteSampler.ADCFeed.unpack(struct.pack("<H", 3))
        self.assertEqual(pkt.header.sample_sequence_number, 3)
        self.assertEqual(pkt.samples, [])


class OTAVectorTest(unittest.TestCase):
    def test_control_unpack(self):
        self.assertIs(api.OTA.Control.unpack(b"\x02"), api.OTACode.REQUEST_ACK)

    def test_control_pack(self):
        self.assertEqual(api.OTA.Control.pack(api.OTACode.DONE_ACK), b"\x05")

    def test_data_pack_passthrough(self):
        self.assertEqual(api.OTA.Data.pack(b"\xde\xad\xbe\xef"), b"\xde\xad\xbe\xef")


class TxPowerVectorTest(unittest.TestCase):
    def test_pack_negative_dbm(self):
        self.assertEqual(api.TxPower.TxPowerSet.pack(-4), b"\xfc")

    def test_unpack_negative_dbm(self):
        self.assertEqual(api.DeviceInfo.TxPowerLevel.unpack(b"\xfc"), -4)


class DeviceInfoVectorTest(unittest.TestCase):
    def test_string_unpack(self):
        self.assertEqual(api.DeviceInfo.ManufacturerName.unpack(b"K3 Engineering"), "K3 Engineering")


if __name__ == "__main__":
    unittest.main()
