"""API for the dynamite sampler board."""

from typing import Generic, TypeVar
import dataclasses


## BLE services and characteristics structure
# Baseclasses and typing boiler plate stuff to make the actual API a bit more readable.
class Service:
    UUID: str


class Characteristic:
    UUID: str


class Struct:
    pass


class uint8:
    pass


class int8:
    pass


class uint16:
    pass


class int24:
    pass


class u32:
    pass


class Utf8String:
    pass


class Bytes:
    pass


# TODO not sure if this is the right way to do this
class Array(TypeVar):
    pass


class Enum:
    pass


_UnpackResultT = TypeVar("_UnpackResultT")
_PackType = TypeVar("_PackType")


class CharacteristicRead(Characteristic, Generic[_UnpackResultT]):
    """Base class for BLE characteristics that can be read."""

    pass


class CharacteristicWrite(Characteristic, Generic[_PackType]):
    """Base class for BLE characteristics that can be writen."""

    pass


class CharacteristicNotify(Characteristic, Generic[_UnpackResultT]):
    """Base class for BLE characteristics that can be read."""

    pass


class CharacteristicIndicate(Characteristic, Generic[_UnpackResultT]):
    """Base class for BLE characteristics that can be read."""

    pass


### Dynamite Sampler API classes

## dataclasses TODO change
# TODO figure out where to specify little endian


@dataclasses.dataclass
class OTACode:
    # TODO figure out the best way to encode what the code is. Maybe enum?
    # NOP = bytearray.fromhex("00")

    # REQUEST = bytearray.fromhex("01")
    # REQUEST_ACK = bytearray.fromhex("02")
    # REQUEST_NAK = bytearray.fromhex("03")

    # DONE = bytearray.fromhex("04")
    # DONE_ACK = bytearray.fromhex("05")
    # DONE_NAK = bytearray.fromhex("06")
    code: uint8


@dataclasses.dataclass
class ADCConfigData:
    """Information how the ADC is configured via the registers."""

    version: uint8
    # TODO the registers need parsing too. Maybe use ctypes? Maybe something else?
    id: uint16
    status: uint16
    mode: uint16
    clock: uint16
    pga: uint16


@dataclasses.dataclass
class FeedHeader:
    """Packet header prepended to each BLE ADC feed notification."""

    sample_sequence_number: uint16  # Running sample counter


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
    samples: Array[FeedData]  # TODO is this the best way to represent this?


## Services


class DynamiteSampler(Service):
    """Service that sends the ADC values (the force measurements).
    This service's UUID is advertised, and can be used to filter scanning."""

    UUID = "e331016b-6618-4f8f-8997-1a2c7c9e5fa3"

    class ADCFeed(CharacteristicNotify[FeedPacket]):
        """Characteristic that streams the ADC values. Only has BLE Notifications.

        Each notification is a packet with a 2-byte header (see FeedHeader) followed by
        concatenated 12-byte ADC samples (4 channels x 3 bytes each, signed little-endian).
        """

        UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"

    class ADCConfig(CharacteristicRead[ADCConfigData]):
        """Characteristic (Read-only) of the ADC configuration values."""

        UUID = "adcc0f19-2575-4502-9a48-0e99974eb34f"


class OTA(Service):
    UUID = "d6f1d96d-594c-4c53-b1c6-144a1dfde6d8"

    class Control(CharacteristicRead[OTACode], CharacteristicWrite[OTACode]):
        UUID = "7ad671aa-21c0-46a4-b722-270e3ae3d830"

    class Data:
        UUID = "23408888-1f40-4cd8-9b89-ca8d45f8a5b0"


class TxPower(Service):
    UUID = "74788a4c-72aa-4180-a478-59e969b959c9"

    class TxPowerSet(CharacteristicWrite[int8]):
        """set TX power in dbm"""

        UUID = "7478c418-35d3-4c3d-99d9-2de090159664"


class DeviceInfo(Service):
    """Read-only device info. The UUIDs are 16 bit hex."""

    UUID = "180A"

    class ManufacturerName(CharacteristicRead[Utf8String]):
        UUID = "2A29"

    class FirmwareRevision(CharacteristicRead[Utf8String]):
        UUID = "2A26"

    class HardwareRevision(CharacteristicRead[Utf8String]):
        """Board model, e.g. 'v700P'"""

        UUID = "2A27"

    class TxPowerLevel(CharacteristicRead[int8]):
        """get TX power in dbm"""

        UUID = "2A07"
