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
    ldr r0, =0x40000000
    ldr r1, =0x40400000
    ldr r2, =0x40200000
    ldr r7, =0xfffffe40
    ldr r8, =0xa5000001
    ldr r9, =0xfffffa30
    mov r10, #0x10
    str r10, [r9, #4]  /* PIOC CODR: assert CE */
page_loop:
    str r8, [r7]
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
    subs r6, r6, #1
    bne byte_loop
    add r4, r4, #1
    subs r5, r5, #1
    bne page_loop
    mov r10, #0x10
    str r10, [r9]      /* deassert CE */
.global done
done:
    b done
    .ltorg
