# AUTO-GENERATED FILE. DO NOT EDIT.
import struct
from enum import IntEnum
from dataclasses import dataclass
from typing import List, Generic, TypeVar, ClassVar


# Helper to unpack 3-byte signed integers (int24)
def _unpack_int24(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 3], byteorder="little", signed=True)


# Helper to pack 3-byte signed integers (int24)
def _pack_int24(value: int) -> bytes:
    return value.to_bytes(3, byteorder="little", signed=True)


# --- BASE CLASSES ---
class BLEService:
    UUID: str
    advertised: bool = False


class BLECharacteristic:
    UUID: str


_UnpackResultT = TypeVar("_UnpackResultT")
_PackType = TypeVar("_PackType")


class BLECharacteristicRead(BLECharacteristic, Generic[_UnpackResultT]):
    """Base class for BLE characteristics that can be read."""

    @classmethod
    def unpack(cls, b: bytearray | bytes) -> _UnpackResultT:
        """Parses raw characteristic data into some sort of object."""
        raise NotImplementedError("Subclasses must implement the unpack method.")


class BLECharacteristicWrite(BLECharacteristic, Generic[_PackType]):
    """Base class for BLE characteristics that can be writen."""

    @classmethod
    def pack(cls, data: _PackType) -> bytes | bytearray:
        """Pack data into bytes to send."""
        raise NotImplementedError("Subclasses must implement the pack method.")


# --- ENUMS ---
class OTACode(IntEnum):
    NOP = 0
    REQUEST = 1
    REQUEST_ACK = 2
    REQUEST_NAK = 3
    DONE = 4
    DONE_ACK = 5
    DONE_NAK = 6


# --- DATACLASSES / STRUCTS ---
@dataclass
class ADCConfigData:
    version: int
    id: int
    status: int
    mode: int
    clock: int
    pga: int

    @classmethod
    def unpack(cls, data: bytes) -> "ADCConfigData":
        offset = 0
        _version = struct.unpack_from("<B", data, offset)[0]
        offset += 1
        _id = struct.unpack_from("<H", data, offset)[0]
        offset += 2
        _status = struct.unpack_from("<H", data, offset)[0]
        offset += 2
        _mode = struct.unpack_from("<H", data, offset)[0]
        offset += 2
        _clock = struct.unpack_from("<H", data, offset)[0]
        offset += 2
        _pga = struct.unpack_from("<H", data, offset)[0]
        offset += 2
        return cls(_version, _id, _status, _mode, _clock, _pga)


@dataclass
class FeedData:
    ch0: int
    ch1: int
    ch2: int
    ch3: int

    @classmethod
    def unpack(cls, data: bytes) -> "FeedData":
        offset = 0
        _ch0 = _unpack_int24(data, offset)
        offset += 3
        _ch1 = _unpack_int24(data, offset)
        offset += 3
        _ch2 = _unpack_int24(data, offset)
        offset += 3
        _ch3 = _unpack_int24(data, offset)
        offset += 3
        return cls(_ch0, _ch1, _ch2, _ch3)


@dataclass
class FeedHeader:
    sample_sequence_number: int

    @classmethod
    def unpack(cls, data: bytes) -> "FeedHeader":
        offset = 0
        _sample_sequence_number = struct.unpack_from("<H", data, offset)[0]
        offset += 2
        return cls(_sample_sequence_number)


@dataclass
class FeedPacket:
    header: FeedHeader
    samples: List[FeedData]

    @classmethod
    def unpack(cls, data: bytes) -> "FeedPacket":
        offset = 0
        _header, bytes_read = FeedHeader.unpack_with_size(data[offset:])
        offset += bytes_read
        # Variable length list unpacking
        _samples = []
        while offset < len(data):
            item, bytes_read = FeedData.unpack_with_size(data[offset:])
            _samples.append(item)
            offset += bytes_read
        return cls(_header, _samples)


# --- BLE SERVICES ---
class DeviceInfo(BLEService):
    UUID = "180A"

    class FirmwareRevision(BLECharacteristicRead[str]):
        UUID = "2A26"

        @staticmethod
        def unpack(b: bytearray | bytes) -> str:
            data = bytes(b)  # Cast to immutable bytes for standard unpacking
            return data.decode("utf-8")

    class HardwareRevision(BLECharacteristicRead[str]):
        UUID = "2A27"

        @staticmethod
        def unpack(b: bytearray | bytes) -> str:
            data = bytes(b)  # Cast to immutable bytes for standard unpacking
            return data.decode("utf-8")

    class ManufacturerName(BLECharacteristicRead[str]):
        UUID = "2A29"

        @staticmethod
        def unpack(b: bytearray | bytes) -> str:
            data = bytes(b)  # Cast to immutable bytes for standard unpacking
            return data.decode("utf-8")

    class TxPowerLevel(BLECharacteristicRead[int]):
        UUID = "2A07"

        @staticmethod
        def unpack(b: bytearray | bytes) -> int:
            data = bytes(b)  # Cast to immutable bytes for standard unpacking
            return struct.unpack("<b", data)[0]


class DynamiteSampler(BLEService):
    UUID = "e331016b-6618-4f8f-8997-1a2c7c9e5fa3"

    class ADCConfig(BLECharacteristicRead[ADCConfigData]):
        UUID = "adcc0f19-2575-4502-9a48-0e99974eb34f"

        @staticmethod
        def unpack(b: bytearray | bytes) -> ADCConfigData:
            data = bytes(b)  # Cast to immutable bytes for standard unpacking
            return ADCConfigData.unpack(data)

    class ADCFeed(BLECharacteristicRead[FeedPacket]):
        UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

        @staticmethod
        def unpack(b: bytearray | bytes) -> FeedPacket:
            data = bytes(b)  # Cast to immutable bytes for standard unpacking
            return FeedPacket.unpack(data)


class OTA(BLEService):
    UUID = "d6f1d96d-594c-4c53-b1c6-144a1dfde6d8"

    class Control(BLECharacteristicRead[OTACode], BLECharacteristicWrite[OTACode]):
        UUID = "7ad671aa-21c0-46a4-b722-270e3ae3d830"

        @staticmethod
        def unpack(b: bytearray | bytes) -> OTACode:
            data = bytes(b)  # Cast to immutable bytes for standard unpacking
            return OTACode(struct.unpack("<B", data)[0])

        @staticmethod
        def pack(data: OTACode) -> bytes | bytearray:
            return struct.pack("<B", data.value)

    class Data(BLECharacteristicWrite[bytes]):
        UUID = "23408888-1f40-4cd8-9b89-ca8d45f8a5b0"

        @staticmethod
        def pack(data: bytes) -> bytes | bytearray:
            return data


class TxPower(BLEService):
    UUID = "74788a4c-72aa-4180-a478-59e969b959c9"

    class TxPowerSet(BLECharacteristicWrite[int]):
        UUID = "7478c418-35d3-4c3d-99d9-2de090159664"

        @staticmethod
        def pack(data: int) -> bytes | bytearray:
            return struct.pack("<b", data)
