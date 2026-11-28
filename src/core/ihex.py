"""Strict Intel HEX parsing and PIC flat-memory conversion.

Addresses in ``HexImage.data`` are Intel HEX byte addresses. ``to_flat`` exposes
PIC word addresses for program/configuration and byte addresses for EEPROM, as
used by the MCU database and the ArdPicProg user interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Mapping, Optional, Set


class IHexError(ValueError):
    """Malformed or unsupported Intel HEX input."""


@dataclass
class HexImage:
    data: Dict[int, int] = field(default_factory=dict)

    def size(self) -> int:
        return len(self.data)

    def is_empty(self) -> bool:
        return not self.data

    def to_flat(self) -> Dict[int, int]:
        """Convert byte-addressed Intel HEX records into PIC flat addresses.

        PIC program/config words are little-endian pairs at doubled addresses;
        EEPROM bytes are represented directly at HEX byte address 0x4200+ and
        translated to flat address 0x2100+.
        """
        flat: Dict[int, int] = {}
        buckets: Dict[int, list[Optional[int]]] = {}
        for byte_addr, value in self.data.items():
            if not 0 <= byte_addr <= 0xFFFF or not 0 <= value <= 0xFF:
                raise IHexError(f"Invalid byte address/value: {byte_addr:#x}={value!r}")
            word_addr, lane = divmod(byte_addr, 2)
            word = buckets.setdefault(word_addr, [None, None])
            word[lane] = value
        for addr, pair in buckets.items():
            if pair[0] is None or pair[1] is None:
                raise IHexError(f"Unpaired byte in 14-bit PIC HEX word at flat address 0x{addr:04X}")
            value = (pair[1] << 8) | pair[0]
            flat[addr] = (value & 0x00FF) if 0x2100 <= addr <= 0x22FF else (value & 0x3FFF)
        return flat

    @classmethod
    def from_flat(cls, flat: Mapping[int, int], skip_addrs: Iterable[int] = ()) -> "HexImage":
        skip: Set[int] = set(skip_addrs)
        out = cls()
        for addr, word in sorted(flat.items()):
            if addr in skip:
                continue
            if not isinstance(addr, int) or not isinstance(word, int):
                raise IHexError("Flat HEX addresses and values must be integers")
            if addr < 0 or not 0 <= word <= 0xFFFF:
                raise IHexError(f"Invalid flat value at {addr!r}: {word!r}")
            byte_addr = addr * 2
            if byte_addr + 1 > 0xFFFF:
                raise IHexError(f"Address {addr:#x} exceeds supported Intel HEX range")
            if 0x2100 <= addr <= 0x22FF:
                if word > 0xFF:
                    raise IHexError(f"EEPROM byte at {addr:#06x} exceeds 8 bits")
                high = 0
            else:
                high = (word >> 8) & 0x3F
            out.data[byte_addr] = word & 0xFF
            out.data[byte_addr + 1] = high
        return out

    @classmethod
    def from_hex(cls, text: str) -> "HexImage":
        image = cls()
        base = 0
        eof = False
        for line_no, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line:
                continue
            if eof:
                raise IHexError(f"Unexpected record after EOF at line {line_no}")
            if not line.startswith(":"):
                raise IHexError(f"Line {line_no}: record must start with ':'")
            try:
                rec = bytes.fromhex(line[1:])
            except ValueError as exc:
                raise IHexError(f"Line {line_no}: non-hexadecimal record") from exc
            if len(rec) < 5:
                raise IHexError(f"Line {line_no}: record is too short")
            count, addr_hi, addr_lo, kind = rec[:4]
            if len(rec) != count + 5:
                raise IHexError(f"Line {line_no}: byte count does not match record length")
            if sum(rec) & 0xFF:
                raise IHexError(f"Line {line_no}: checksum mismatch")
            address = (addr_hi << 8) | addr_lo
            payload = rec[4:-1]
            if kind == 0x00:
                absolute = base + address
                if absolute + count > 0x10000:
                    raise IHexError(f"Line {line_no}: data exceeds supported 64 KiB address space")
                for i, value in enumerate(payload):
                    a = absolute + i
                    if a in image.data and image.data[a] != value:
                        raise IHexError(f"Line {line_no}: conflicting data at address 0x{a:04X}")
                    image.data[a] = value
            elif kind == 0x01:
                if count or address:
                    raise IHexError(f"Line {line_no}: malformed EOF record")
                eof = True
            elif kind == 0x02:
                if count != 2 or address:
                    raise IHexError(f"Line {line_no}: malformed extended segment address")
                base = int.from_bytes(payload, "big") << 4
            elif kind == 0x04:
                if count != 2 or address:
                    raise IHexError(f"Line {line_no}: malformed extended linear address")
                base = int.from_bytes(payload, "big") << 16
            elif kind in (0x03, 0x05):
                # Start-segment/start-linear records do not contain memory.
                if count != 4 or address:
                    raise IHexError(f"Line {line_no}: malformed start-address record")
            else:
                raise IHexError(f"Line {line_no}: unsupported record type 0x{kind:02X}")
        if not eof:
            raise IHexError("Missing Intel HEX EOF record")
        return image

    @classmethod
    def load(cls, path: str | Path) -> "HexImage":
        try:
            return cls.from_hex(Path(path).read_text(encoding="ascii"))
        except UnicodeDecodeError as exc:
            raise IHexError("HEX file is not ASCII text") from exc
        except OSError as exc:
            raise IHexError(f"Cannot read HEX file: {exc}") from exc

    def to_hex(self, record_size: int = 16) -> str:
        if not 1 <= record_size <= 255:
            raise ValueError("record_size must be from 1 to 255")
        lines = []
        addresses = sorted(self.data)
        i = 0
        while i < len(addresses):
            start = addresses[i]
            if not 0 <= start <= 0xFFFF:
                raise IHexError(f"Address outside 16-bit HEX range: {start}")
            chunk = [self.data[start]]
            i += 1
            while (i < len(addresses) and len(chunk) < record_size
                   and addresses[i] == start + len(chunk)):
                chunk.append(self.data[addresses[i]])
                i += 1
            lines.append(self._record(start, 0, bytes(chunk)))
        lines.append(self._record(0, 1, b""))
        return "\n".join(lines) + "\n"

    @staticmethod
    def _record(address: int, kind: int, payload: bytes) -> str:
        body = bytes((len(payload), (address >> 8) & 0xFF, address & 0xFF, kind)) + payload
        checksum = (-sum(body)) & 0xFF
        return ":" + (body + bytes((checksum,))).hex().upper()


def load_hex_file(path: str | Path) -> HexImage:
    return HexImage.load(path)
