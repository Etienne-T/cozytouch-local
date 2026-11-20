ENTRY(_start)
SECTIONS {
    . = 0x00300000;
    .text : { *(.text.start) *(.text*) *(.rodata*) }
    .data : { *(.data*) }
    .bss : { *(.bss*) *(COMMON) }
    /DISCARD/ : { *(.comment) *(.note*) *(.ARM.attributes) *(.ARM.exidx*) }
}
