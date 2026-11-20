#!/usr/bin/env python3
from pathlib import Path
import sys

path = Path(sys.argv[1]) / "drivers/mtd/nand/raw/atmel/nand-controller.c"
source = path.read_text()
if "cozytouch,read-only-nand" in source:
    sys.exit(0)
substitutions = {
    "\treturn nc->caps->ops->exec_op(nand, op, check_only);": """
	/* Rescue uses the SMC read path only. */
	if (chip->options & NAND_ROM) {
		unsigned int i;

		for (i = 0; i < op->ninstrs; i++) {
			const struct nand_op_instr *instr = &op->instrs[i];

			switch (instr->type) {
			case NAND_OP_ADDR_INSTR:
			case NAND_OP_DATA_IN_INSTR:
			case NAND_OP_WAITRDY_INSTR:
				continue;
			case NAND_OP_CMD_INSTR:
				switch (instr->ctx.cmd.opcode) {
				case NAND_CMD_READ0:
				case NAND_CMD_READ1:
				case NAND_CMD_READOOB:
				case NAND_CMD_READSTART:
				case NAND_CMD_RNDOUT:
				case NAND_CMD_RNDOUTSTART:
				case NAND_CMD_READID:
				case NAND_CMD_PARAM:
				case NAND_CMD_STATUS:
				case NAND_CMD_RESET:
				case NAND_CMD_GET_FEATURES:
					continue;
				}
				break;
			default:
				break;
			}
			return -EROFS;
		}
	}

	return nc->caps->ops->exec_op(nand, op, check_only);""".lstrip("\n"),
    "\tret = nand_scan(chip, nand->numcs);": """
	if (of_property_read_bool(nand_get_flash_node(chip), "cozytouch,read-only-nand")) {
		if (nc->caps->ops->exec_op != atmel_smc_nand_exec_op ||
		    of_property_read_bool(nand_get_flash_node(chip), "nand-on-flash-bbt"))
			return -EINVAL;
		chip->options |= NAND_ROM;
		dev_info(nc->dev, "Cozytouch NAND read-only command guard; RAM BBT only\\n");
	}

	ret = nand_scan(chip, nand->numcs);""".lstrip("\n"),
}
for before, after in substitutions.items():
    if source.count(before) != 1:
        raise SystemExit("Unexpected atmel NAND source")
    source = source.replace(before, after)
path.write_text(source)

