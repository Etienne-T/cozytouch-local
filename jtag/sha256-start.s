.syntax unified
.cpu arm926ej-s
.arm
.section .text.start,"ax"
.global _start
_start:
    ldr sp, =0x00306f00
    bl hash_buffer
.global hash_done
hash_done:
    b hash_done
    .ltorg
