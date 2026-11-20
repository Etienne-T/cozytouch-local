# Read-only checks while the owned CPU is halted. No resume or device writes.
if {[target current] ne "at91sam9g25.cpu"} {error "Unexpected target"}
if {[at91sam9g25.cpu curstate] ne "halted"} {error "Target is not halted"}
set preflight_wdt [lindex [read_memory 0xfffffe44 32 1 phys] 0]
if {$preflight_wdt != 0x1fff2fff} {error "Watchdog mode changed since qualification"}
set preflight_straps [lindex [read_memory 0xfffff83c 32 1 phys] 0]
if {[expr {$preflight_straps & 0x2a000000}] != 0x0a000000} {error "Board straps mismatch"}
# Verify CP15 read command support before any irreversible CPU-context change.
set preflight_sctlr [arm mrc 15 0 1 0 0]
if {[expr {$preflight_sctlr & 1}] != 1} {error "Expected the running Linux MMU context"}
echo READ_ONLY_PREFLIGHT_PASSED
