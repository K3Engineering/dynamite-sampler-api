# AUTO-GENERATED FILE. DO NOT EDIT.
import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Generic, TypeVar


def _unpack_int24(data: bytes, offset: int) -> int:
    """Unpacks a 3-byte little-endian signed integer."""
    return int.from_bytes(data[offset : offset + 3], byteorder="little", signed=True)


def _pack_int24(value: int) -> bytes:
    """Packs an integer as a 3-byte little-endian signed integer."""
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
    """Base class for BLE characteristics that can be written."""

    @classmethod
    def pack(cls, data: _PackType) -> bytes:
        """Pack data into bytes to send."""
        raise NotImplementedError("Subclasses must implement the pack method.")


# --- ENUMS ---
class OTACode(IntEnum):
    """
    OTA command and response codes.
    """

    NOP = 0x00
    REQUEST = 0x01
    REQUEST_ACK = 0x02
    REQUEST_NAK = 0x03
    DONE = 0x04
    DONE_ACK = 0x05
    DONE_NAK = 0x06


# --- DATACLASSES / STRUCTS ---
@dataclass
class ADCConfigData:
    """
    Information how the ADC is configured via the registers.
    """

    version: int
    id: int
    status: int
    mode: int
    clock: int
    pga: int

    @classmethod
    def unpack_with_size(cls, data: bytes) -> tuple["ADCConfigData", int]:
        """Unpacks this struct from raw bytes.

        Returns the instantiated object and the number of bytes consumed.
        """
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
        return cls(_version, _id, _status, _mode, _clock, _pga), offset

    @classmethod
    def unpack(cls, data: bytes) -> "ADCConfigData":
        """Unpacks this struct from raw bytes."""
        obj, _ = cls.unpack_with_size(data)
        return obj


@dataclass
class FeedData:
    """
    A single ADC sample that contains all 4 channels.
    """

    ch0: int
    ch1: int
    ch2: int
    ch3: int

    @classmethod
    def unpack_with_size(cls, data: bytes) -> tuple["FeedData", int]:
        """Unpacks this struct from raw bytes.

        Returns the instantiated object and the number of bytes consumed.
        """
        offset = 0
        _ch0 = _unpack_int24(data, offset)
        offset += 3
        _ch1 = _unpack_int24(data, offset)
        offset += 3
        _ch2 = _unpack_int24(data, offset)
        offset += 3
        _ch3 = _unpack_int24(data, offset)
        offset += 3
        return cls(_ch0, _ch1, _ch2, _ch3), offset

    @classmethod
    def unpack(cls, data: bytes) -> "FeedData":
        """Unpacks this struct from raw bytes."""
        obj, _ = cls.unpack_with_size(data)
        return obj


@dataclass
class FeedHeader:
    """
    Packet header prepended to each BLE ADC feed notification.
    """

    sample_sequence_number: int

    @classmethod
    def unpack_with_size(cls, data: bytes) -> tuple["FeedHeader", int]:
        """Unpacks this struct from raw bytes.

        Returns the instantiated object and the number of bytes consumed.
        """
        offset = 0
        _sample_sequence_number = struct.unpack_from("<H", data, offset)[0]
        offset += 2
        return cls(_sample_sequence_number), offset

    @classmethod
    def unpack(cls, data: bytes) -> "FeedHeader":
        """Unpacks this struct from raw bytes."""
        obj, _ = cls.unpack_with_size(data)
        return obj


@dataclass
class FeedPacket:
    """
    A full BLE ADC feed notification: header + list of samples.
    """

    header: FeedHeader
    samples: list[FeedData]

    @classmethod
    def unpack_with_size(cls, data: bytes) -> tuple["FeedPacket", int]:
        """Unpacks this struct from raw bytes.

        Returns the instantiated object and the number of bytes consumed.
        """
        offset = 0
        _header, bytes_read = FeedHeader.unpack_with_size(data[offset:])
        offset += bytes_read
        _samples = []
        while offset < len(data):
            item, bytes_read = FeedData.unpack_with_size(data[offset:])
            _samples.append(item)
            offset += bytes_read
        return cls(_header, _samples), offset

    @classmethod
    def unpack(cls, data: bytes) -> "FeedPacket":
        """Unpacks this struct from raw bytes."""
        obj, _ = cls.unpack_with_size(data)
        return obj


# --- BLE SERVICES ---
class DeviceInfo(BLEService):
    """
    Read-only device info.
    """

    UUID = "180A"
    advertised = False

    class FirmwareRevision(BLECharacteristicRead[str]):
        """
        Firmware revision string.
        """

        UUID = "2A26"

        @classmethod
        def unpack(cls, b: bytearray | bytes) -> str:
            data = bytes(b)
            return data.decode("utf-8")

    class HardwareRevision(BLECharacteristicRead[str]):
        """
        Hardware revision string.
        """

        UUID = "2A27"

        @classmethod
        def unpack(cls, b: bytearray | bytes) -> str:
            data = bytes(b)
            return data.decode("utf-8")

    class ManufacturerName(BLECharacteristicRead[str]):
        """
        Manufacturer name string.
        """

        UUID = "2A29"

        @classmethod
        def unpack(cls, b: bytearray | bytes) -> str:
            data = bytes(b)
            return data.decode("utf-8")

    class TxPowerLevel(BLECharacteristicRead[int]):
        """
        Current transmit power level in dBm.
        """

        UUID = "2A07"

        @classmethod
        def unpack(cls, b: bytearray | bytes) -> int:
            data = bytes(b)
            return struct.unpack("<b", data)[0]


class DynamiteSampler(BLEService):
    """
    Service that sends the ADC values (the force measurements).
    """

    UUID = "e331016b-6618-4f8f-8997-1a2c7c9e5fa3"
    advertised = True

    class ADCConfig(BLECharacteristicRead[ADCConfigData]):
        """
        Read-only ADC configuration values.
        """

        UUID = "adcc0f19-2575-4502-9a48-0e99974eb34f"

        @classmethod
        def unpack(cls, b: bytearray | bytes) -> ADCConfigData:
            data = bytes(b)
            return ADCConfigData.unpack(data)

    class ADCFeed(BLECharacteristicRead[FeedPacket]):
        """
        Streams the ADC values. Concatenated 12-byte ADC samples.
        """

        UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

        @classmethod
        def unpack(cls, b: bytearray | bytes) -> FeedPacket:
            data = bytes(b)
            return FeedPacket.unpack(data)


class OTA(BLEService):
    """
    Over-the-air firmware update service.
    """

    UUID = "d6f1d96d-594c-4c53-b1c6-144a1dfde6d8"
    advertised = False

    class Control(BLECharacteristicRead[OTACode], BLECharacteristicWrite[OTACode]):
        """
        OTA control point used to exchange command and response codes.
        """

        UUID = "7ad671aa-21c0-46a4-b722-270e3ae3d830"

        @classmethod
        def unpack(cls, b: bytearray | bytes) -> OTACode:
            data = bytes(b)
            return OTACode(struct.unpack("<B", data)[0])

        @classmethod
        def pack(cls, data: OTACode) -> bytes:
            return struct.pack("<B", data.value)

    class Data(BLECharacteristicWrite[bytes]):
        """
        OTA data stream used to write firmware image chunks.
        """

        UUID = "23408888-1f40-4cd8-9b89-ca8d45f8a5b0"

        @classmethod
        def pack(cls, data: bytes) -> bytes:
            return data


class TxPower(BLEService):
    """
    Service to configure the radio transmit power.
    """

    UUID = "74788a4c-72aa-4180-a478-59e969b959c9"
    advertised = False

    class TxPowerSet(BLECharacteristicWrite[int]):
        """
        Sets the TX power in dBm.
        """

        UUID = "7478c418-35d3-4c3d-99d9-2de090159664"

        @classmethod
        def pack(cls, data: int) -> bytes:
            return struct.pack("<b", data)
