# OFFLINE CANDIDATE. Owner must review, halt the CPU, and set
# COZY_ALLOW_QUIESCE=reviewed before sourcing. No halt/resume/reset is hidden here.
# Once COZY_QUIESCE_COMMITTED is set, do not resume the old Linux context.
proc cozy_read32 {address} {
    set value_text [mdw phys $address 1]
    if {![regexp {0x[0-9a-fA-F]+:[ 	]+([0-9a-fA-F]+)} $value_text match value_hex]} {
        error "Cannot parse physical read at $address: $value_text"
    }
    scan $value_hex %x value
    if {$value == 0xffffffff} {error "All-ones physical read at $address"}
    return $value
}
proc cozy_assert_mask {address mask expected label} {
    set value [cozy_read32 $address]
    if {[expr {$value & $mask}] != $expected} {
        error "$label mismatch at $address: [format 0x%08x $value]"
    }
    return $value
}
proc cozy_poll_mask {address mask expected attempts label} {
    for {set i 0} {$i < $attempts} {incr i} {
        set value [cozy_read32 $address]
        if {[expr {$value & $mask}] == $expected} {return $value}
        sleep 1
    }
    error "$label did not reach expected state at $address"
}

if {![info exists COZY_ALLOW_QUIESCE] || $COZY_ALLOW_QUIESCE ne "reviewed"} {
    error "Candidate quiescence requires owner review token"
}
set cozy_target [target current]
if {[$cozy_target curstate] ne "halted"} {error "CPU must already be halted"}

# Read/validate every precondition before changing any peripheral.
cozy_assert_mask 0xfffff808 0x2a000000 0x2a000000 PIOC_GPIO_INPUT_STRAPS
cozy_assert_mask 0xfffff818 0x2a000000 0 PIOC_STRAP_NOT_OUTPUT
cozy_assert_mask 0xfffff83c 0x2a000000 0x0a000000 MINIIO_STRAPS
cozy_assert_mask 0xfffffe44 0xffffffff 0x1fff2fff WATCHDOG_MODE
cozy_assert_mask 0x00600000 0xff 0x10 OHCI_REVISION
cozy_assert_mask 0x00700000 0xffffffff 0x01000010 EHCI_CAPLENGTH_AND_VERSION
cozy_assert_mask 0xf802c014 0x8 0 MACB_TX_NOT_IN_PROGRESS
set cozy_dma0 [cozy_read32 0xffffec30]
if {[expr {$cozy_dma0 & 0xff & ~0x2}] != 0} {error "Unexpected active HDMAC0 channel"}
if {[expr {$cozy_dma0 & 0x2}] != 0} {
    cozy_assert_mask 0xffffec64 0xffffffff 0xf801c018 USART0_RX_ONLY
}
cozy_assert_mask 0xffffee30 0xff 0 HDMAC1_NO_ACTIVE_CHANNEL
set cozy_sa1b [cozy_read32 0xf802c098]
set cozy_sa1t [cozy_read32 0xf802c09c]
set cozy_ohci_control [cozy_read32 0x00600004]
set cozy_ehci_command [cozy_read32 0x00700010]
set cozy_macb_control [cozy_read32 0xf802c000]

set COZY_QUIESCE_COMMITTED 1
echo COZY_PERIPHERAL_COMMIT_DO_NOT_RESUME_OLD_LINUX

# EHCI: stop schedules; wait for their status; disable IRQs; clear RUN/IAAD.
mww phys 0x00700010 [expr {$cozy_ehci_command & ~0x30}]
cozy_poll_mask 0x00700014 0xc000 0 100 EHCI_SCHEDULES_OFF
mww phys 0x00700018 0
mww phys 0x00700010 [expr {$cozy_ehci_command & ~0x71}]
cozy_poll_mask 0x00700014 0x1000 0x1000 100 EHCI_HALTED
cozy_assert_mask 0x00700010 0x71 0 EHCI_RUN_AND_SCHEDULE_BITS_CLEAR

# OHCI: Linux ohci_usb_reset equivalent; retain only RWC and force HCFS RESET.
mww phys 0x00600014 0xffffffff
mww phys 0x00600004 [expr {$cozy_ohci_control & 0x200}]
cozy_assert_mask 0x00600004 0x4fc 0 OHCI_RESET_AND_SCHEDULES_OFF
set cozy_ohci_frame [cozy_read32 0x0060003c]
sleep 20
set cozy_ohci_frame_after [cozy_read32 0x0060003c]
if {$cozy_ohci_frame != $cozy_ohci_frame_after} {error "OHCI frame counter still changes"}

# MACB: no TX is active; disable RX/TX without touching station addresses.
mww phys 0xf802c02c 0xffffffff
mww phys 0xf802c000 [expr {$cozy_macb_control & ~0xc}]
cozy_assert_mask 0xf802c000 0xc 0 MACB_RX_TX_DISABLED
cozy_poll_mask 0xf802c014 0x8 0 100 MACB_TX_IDLE

# HDMAC0/1: match Linux at_dma_off; mask IRQs and confirm all eight channels off.
foreach cozy_dma_base {0xffffec00 0xffffee00} {
    mww phys [expr {$cozy_dma_base + 4}] 0
    mww phys [expr {$cozy_dma_base + 0x1c}] 0xffffffff
    cozy_poll_mask [expr {$cozy_dma_base + 0x30}] 0xff 0 100 HDMAC_CHANNELS_OFF
    cozy_assert_mask [expr {$cozy_dma_base + 4}] 1 0 HDMAC_CONTROLLER_OFF
}
if {[cozy_read32 0xf802c098] != $cozy_sa1b || [cozy_read32 0xf802c09c] != $cozy_sa1t} {
    error "MACB station address changed unexpectedly"
}
echo COZY_QUIESCENCE_CHECKS_PASSED
