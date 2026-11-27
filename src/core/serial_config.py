"""Serial settings for the ProgramPic Arduino runtime connection."""

# ProgramPic firmware initializes Serial at this fixed rate. Arduino bootloader
# upload uses a separate port session and its own board-specific baud rate.
PROGRAMMER_BAUD = 9600
