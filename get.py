#!/usr/bin/env python3

"""
Creates the config.json file that is used to get the ghidra manuals and place
them in the ghidra installation. Does not populate the URL fields though.
"""

#TODO: - Implement UPDATE_OLD_CONFIG
#      - Popen the head command
#      - Combine get_ghidra_manual and get.py

UPDATE_OLD_CONFIG = False
CONFIG_FILE = "config.json"

# run `head -n1 $(find . -name "*.idx")` in your ghidra folder installation
manuals = """==> ./Ghidra/Processors/PA-RISC/data/manuals/pa11_acd.idx <==
@pa11_acd.pdf[PA-RISC 1.1 Architecture and Instruction Set Reference Manual, HP Part Number: 09740-90039, February 1994, Third Edition]

==> ./Ghidra/Processors/ARM/data/manuals/ARM.idx <==
@Armv7AR_errata.pdf[ARM Architecture Reference Manual - ARMv7A and ARMv7-R edition Errata markup, July, 2011 (ARM DDI 0406B_errata_2011_Q2)]

==> ./Ghidra/Processors/TI_MSP430/data/manuals/MSP430.idx <==
@MSP430.pdf[TI MSP430x2xx Family User's Guide, 2008, SLAU144E]

==> ./Ghidra/Processors/HCS08/data/manuals/HC08.idx <==
@CPU08RM.pdf[ Rev. 4 02/2006 M68HC08 Microcontrollers, NXP.com ]

==> ./Ghidra/Processors/HCS08/data/manuals/HCS08.idx <==
@HCS08RMV1.pdf[ Rev. 2 05/2007 M68HCS08 Microcontrollers, NXP.com ]

==> ./Ghidra/Processors/HCS08/data/manuals/HC05.idx <==
@M68HC05TB.pdf[ Rev. 2.0 1998 M68HC05 Family, Understanding Small Microcontrollers, NXP.com ]

==> ./Ghidra/Processors/6502/data/manuals/6502.idx <==
@mcs6500_family_programming_manual.pdf [MCS 6500 Microcomputer Family Programming Manual, January 1976]

==> ./Ghidra/Processors/6502/data/manuals/65c02.idx <==
@wdc_65816_programming_manual.pdf [Programming the 65816 - Including the 6502, 65C02 and 65802, 2007]

==> ./Ghidra/Processors/CR16/data/manuals/CR16.idx <==
@prog16c.pdf [ Texas Instruments (formerly National Semiconductor), CompactRISC, CR16C Programmer’s Reference Manual. Part Number: 424521772-101. ]

==> ./Ghidra/Processors/AARCH64/data/manuals/AARCH64.idx <==
@DDI0487G_b_armv8_arm.pdf[ARM Architecture Reference Manual - ARMv8, for ARMv8-A architecture profile, 22 July 2021 (ARM DDI DDI0487G.b)]

==> ./Ghidra/Processors/MCS96/data/manuals/MCS96.idx <==
@1991_Intel_16-Bit_Embedded_Controller_Handbook.pdf[1991 Intel 16-Bit Embedded Controller Handbook]

==> ./Ghidra/Processors/V850/data/manuals/v850.idx <==
@r01us0001ej0100_v850e2m.pdf [V850E2M User?s Manual: Architecture RENESAS MCU V850E2M Microprocessor Core]

==> ./Ghidra/Processors/PIC/data/manuals/PIC-18.idx <==
@PIC18_14702.pdf [PIC18CXX2 High-Performance Microcontrollers with 10-Bit A/D, 7/99 (DS39026B)]

==> ./Ghidra/Processors/PIC/data/manuals/PIC-16F.idx <==
@PIC16F_40001761E.pdf [Microchip PIC16LF1554/1559 (DS40001761E)]

==> ./Ghidra/Processors/PIC/data/manuals/PIC24.idx <==
@70000157g.pdf[16-bit MCU and DSC Programmer's Reference Manual - DS70000157G]

==> ./Ghidra/Processors/PIC/data/manuals/PIC-16.idx <==
@PIC16_33023a.pdf [PICmicro� Mid-Range MCU Family Reference Manual, December 1997 (DS33023A)]

==> ./Ghidra/Processors/PIC/data/manuals/PIC-17.idx <==
@PIC17_30289b.pdf [High-Performance 8-bit CMOS EPROM Microcontrollers with 10-bit A/D, 2000 (DS30289B)]

==> ./Ghidra/Processors/PIC/data/manuals/PIC-12.idx <==
@PIC12_40139e.pdf [PIC12C5XX 8-Pin, 8-Bit CMOS Microcontrollers (DS40139E)]

==> ./Ghidra/Processors/8048/data/manuals/8048.idx <==
@8048.pdf [MCS-48 Microcomputer User's Manual, February 1978]

==> ./Ghidra/Processors/MIPS/data/manuals/r4000.idx <==
@r4000.pdf[MIPS R4000 Microprocessor User's Manual, Second Edition, July 2005]

==> ./Ghidra/Processors/MIPS/data/manuals/mipsM16.idx <==
@MD00087-2B-MIPS64BIS-AFP-6.06.pdf [MIPS Architecture For Programmers Volume II-A: The MIPS64 Instruction Set Reference Manual, MD00087, 6.06, December 15, 2016]

==> ./Ghidra/Processors/MIPS/data/manuals/MIPS.idx <==
@mips64v2.pdf[MIPS64 Architecture For Programmers - Volume II, July 2005 (MD00087)]

==> ./Ghidra/Processors/MIPS/data/manuals/mipsMic.idx <==
@MD00087-2B-MIPS64BIS-AFP-6.06.pdf [MIPS Architecture For Programmers Volume II-A: The MIPS64 Instruction Set Reference Manual, MD00087, 6.06, December 15, 2016]

==> ./Ghidra/Processors/HCS12/data/manuals/HCS12.idx <==
@S12XCPUV2.pdf[ CPU12/CPU12X Reference Manual, Rev. v01.04 21 Apr. 2016, nxp.com ]

==> ./Ghidra/Processors/Z80/data/manuals/Z80.idx <==
@UM0080.pdf [Z80 FamilyCPU User Manual, Aug 2016 (UM008011-0816)]

==> ./Ghidra/Processors/Z80/data/manuals/Z180.idx <==
@um0050.pdf [Z8018x Family MPU User Manual (UM005003-0703)]

==> ./Ghidra/Processors/6805/data/manuals/6809.idx <==
@M6809PM.rev0_May83.pdf [MC6809-MC6809E Microprocessor Programming Manual, May 1983 (M6809PM/AD)]

==> ./Ghidra/Processors/SuperH4/data/manuals/superh4.idx <==
@ rej09b0318_sh_4sm.pdf[SH-4 Software Manual Rev 6.00 2006.09]

==> ./Ghidra/Processors/tricore/data/manuals/tricore.idx <==
@tc_v131_instructionset_v138.pdf[TriCore Architecture Volume 2: Instruction Set, V1.3 & V1.3.1]

==> ./Ghidra/Processors/tricore/data/manuals/tricore2.idx <==
@Infineon-TC2xx_Architecture_vol2-UM-v01_00-EN.pdf [TriCore TC1.6P & TC1.6E Instruction Set, User Manual (Volume 2), V1.0 2013-07]

==> ./Ghidra/Processors/Atmel/data/manuals/AVR32.idx <==
@doc32000.pdf [Atmel AVR32 Architecture Document - 04/2011]

==> ./Ghidra/Processors/Atmel/data/manuals/AVR8.idx <==
@atmel-0856-avr-instruction-set-manual.pdf [Atmel AVR Instruction Set Manual, 11/2016 (Rev. 0856L)]

==> ./Ghidra/Processors/PowerPC/data/manuals/PowerISA.idx <==
@PowerISA_V2.06_PUBLIC.pdf[PowerPC® Microprocessor Family: The Programming Environments Manual for 32 and 64-bit Microprocessors, Version 2.3, March 31, 2005]

==> ./Ghidra/Processors/PowerPC/data/manuals/PowerPC.idx <==
@powerpc.pdf[PowerPC� Microprocessor Family: The Programming Environments Manual for 32 and 64-bit Microprocessors, Version 2.3, March 31, 2005]

==> ./Ghidra/Processors/x86/data/manuals/x86.idx <==
@325383-sdm-vol-2abcd.pdf [Intel 64 and IA-32 Architectures Software Developer's Manual Volume 2 (2A, 2B, 2C & 2D): Instruction Set Reference, A-Z, Oct 2019 (325383-071US)]

==> ./Ghidra/Processors/8051/data/manuals/8051.idx <==
@8xc251sx_um.pdf [8XC251SA, 8XC251SB,8XC251SP, 8XC251SQ Embedded Microcontroller User�s Manual, May 1996]

==> ./Ghidra/Processors/68000/data/manuals/68000.idx <==
@M68000PRM.pdf [M68000 FAMILY Programmer�s Reference Manual, 1992 (M68000PRM/AD REV.1)]

==> ./Ghidra/Processors/Sparc/data/manuals/Sparc.idx <==
@SPARCV9.pdf[The SPARC Architecture Manual, Version 9 (SAV09R1459912)]

==> ./Ghidra/Processors/JVM/data/manuals/JVM.idx <==
@jvms8.pdf [The Java Virtual Machine Specification - Jave SE 8 Edition]"""

manual_config_skel = {
    "info": "",
    "path": "",
    "filename": "",
    "urls": []
}

def get_real_path(path):
    idx_name = path.split("/")[-1]

    return path[:path.index(idx_name)]

def parse():
    global manuals

    manuals = manuals.split("\n\n")
    manuals = [line.split("\n") for line in manuals]

    patterns = [
        {
            "start": "==> ",
            "end": " <==",
            "line": 0,
            "field": "path"
        },
        {
            "start": "@",
            "end": "[",
            "line": 1,
            "field": "filename"
        },
        {
            "start": "[",
            "end": "]",
            "line": 1,
            "field": "info"
        },
    ]

    config = {"manuals": []}

    for manual in manuals:
        cur_manual_config = dict(manual_config_skel)

        for pattern_num, pattern in enumerate(patterns):
            if not ("start" in pattern and "end" in pattern and "line" in pattern and "field" in pattern):
                print(f"Warning: Pattern num: {pattern_num} does not have all info.")
            
            start, end, line, field = pattern["start"], pattern["end"], pattern["line"], pattern["field"]

            if line < 0 or line > len(manual):
                print(f"Warning: Pattern {field} line number is out of range. Got line: {line}. Max line is: {len(manual)}")
                print("Skipping...")
                continue

            try:
                l = manual[line]
                cur_manual_config[field] = l[l.index(start)+len(start):l.index(end)]
            except ValueError as e:
                print(f"Warning: Unable to find start ({start}) or end ({end}) in line: {l}")
                print("Skipping...")
                continue
        
        config["manuals"].append(cur_manual_config)

    for manual in config["manuals"]:
        manual["path"] = get_real_path(manual["path"])
        manual["filename"] = manual["filename"].strip()

    import json
    with open(CONFIG_FILE, "w") as config_json_f:
        json.dump(config, config_json_f, indent=4)

    print(f"Manuals info dumped to {CONFIG_FILE}")

if __name__ == "__main__":
    parse()