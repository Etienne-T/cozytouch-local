.syntax unified
.cpu arm926ej-s
.arm
.section .text
.global _start
/* Read-only NAND reader. r4 = first physical page, r5 = page count.
 * r3 = destination RAM. 2048 data + 64 OOB bytes per physical page.
 * Only NAND commands 00h and 30h are issued. No ECC correction.
 * IRQ/FIQ and MMU/caches must be disabled before entry.
 */
_start:
    ldr r12, =0x20300000 /* one AND-of-bytes flag per page */
    mvn r13, #0         /* CRC32 initial state */
    ldr r0, =0x40000000
    ldr r1, =0x40400000
    ldr r2, =0x40200000
    ldr r7, =0xfffffe40
    ldr r8, =0xa5000001
    ldr r9, =0xfffffa30
    mov r10, #0x10
    str r10, [r9, #4]  /* PIOC CODR: assert CE */
page_loop:
    ldr r8, =0xa5000001
    str r8, [r7]
    ldr r8, =0xedb88320 /* reflected CRC32 polynomial */
    mov r11, #0xff
    mov r6, #0
    strb r6, [r1]      /* READ 00h */
    strb r6, [r2]      /* column low */
    strb r6, [r2]      /* column high */
    strb r4, [r2]      /* row low */
    mov r6, r4, lsr #8
    strb r6, [r2]      /* row high: 65536 pages */
    mov r6, #0x30
    strb r6, [r1]      /* READ CONFIRM */
    ldr r6, =100000    /* conservative fixed wait, no GPIO assumption */
read_delay:
    subs r6, r6, #1
    bne read_delay
    mov r6, #0x800
    add r6, r6, #64
byte_loop:
    ldrb r10, [r0]
    strb r10, [r3], #1
    and r11, r11, r10
    eor r13, r13, r10
    mov r14, #8
crc_bit:
    tst r13, #1
    mov r13, r13, lsr #1
    eorne r13, r13, r8
    subs r14, r14, #1
    bne crc_bit
    subs r6, r6, #1
    bne byte_loop
    strb r11, [r12], #1
    add r4, r4, #1
    subs r5, r5, #1
    bne page_loop
    mov r10, #0x10
    str r10, [r9]      /* deassert CE */
    mvn r13, r13       /* final CRC32, compatible with zlib */
.global done
done:
    b done
    .ltorg
