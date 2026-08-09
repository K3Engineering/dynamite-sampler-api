"""API for the dynamite sampler board."""

import enum
import dataclasses
from typing import Generic, TypeVar


# Base primitive types (used as markers for the generator)
class uint8:
    pass


class int8:
    pass


class uint16:
    pass


class int24:
    pass  # 3-byte signed int


class u32:
    pass


class Utf8String:
    pass


class Bytes:
    pass


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


### Dynamite Sampler API classes


class OTACode(enum.IntEnum):
    """OTA command and response codes."""

    NOP = 0x00
    REQUEST = 0x01
    REQUEST_ACK = 0x02
    REQUEST_NAK = 0x03
    DONE = 0x04
    DONE_ACK = 0x05
    DONE_NAK = 0x06


@dataclasses.dataclass
class ADCConfigData:
    """Information how the ADC is configured via the registers."""

    version: uint8
    id: uint16
    status: uint16
    mode: uint16
    clock: uint16
    pga: uint16


@dataclasses.dataclass
class FeedHeader:
    """Packet header prepended to each BLE ADC feed notification."""

    sample_sequence_number: uint16


@dataclasses.dataclass
class FeedData:
    """A single ADC sample that contains all 4 channels."""

    ch0: int24
    ch1: int24
    ch2: int24
    ch3: int24


@dataclasses.dataclass
class FeedPacket:
    """A full BLE ADC feed notification: header + list of samples."""

    header: FeedHeader
    samples: list[FeedData]


## Services


class DynamiteSampler(Service):
    """Service that sends the ADC values (the force measurements)."""

    UUID = "e331016b-6618-4f8f-8997-1a2c7c9e5fa3"
    advertised = True

    class ADCFeed(CharacteristicNotify[FeedPacket]):
        """Streams the ADC values. Concatenated 12-byte ADC samples."""

        UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

    class ADCConfig(CharacteristicRead[ADCConfigData]):
        """Read-only ADC configuration values."""

        UUID = "adcc0f19-2575-4502-9a48-0e99974eb34f"


class OTA(Service):
    UUID = "d6f1d96d-594c-4c53-b1c6-144a1dfde6d8"

    class Control(CharacteristicRead[OTACode], CharacteristicWrite[OTACode]):
        UUID = "7ad671aa-21c0-46a4-b722-270e3ae3d830"

    class Data(CharacteristicWrite[Bytes]):
        UUID = "23408888-1f40-4cd8-9b89-ca8d45f8a5b0"


class TxPower(Service):
    UUID = "74788a4c-72aa-4180-a478-59e969b959c9"

    class TxPowerSet(CharacteristicWrite[int8]):
        """set TX power in dbm"""

        UUID = "7478c418-35d3-4c3d-99d9-2de090159664"


class DeviceInfo(Service):
    """Read-only device info."""

    UUID = "180A"

    class ManufacturerName(CharacteristicRead[Utf8String]):
        UUID = "2A29"

    class FirmwareRevision(CharacteristicRead[Utf8String]):
        UUID = "2A26"

    class HardwareRevision(CharacteristicRead[Utf8String]):
        UUID = "2A27"

    class TxPowerLevel(CharacteristicRead[int8]):
        UUID = "2A07"
