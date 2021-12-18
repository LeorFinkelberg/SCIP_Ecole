import logging.config
import sys

from pathlib2 import Path

LOG_CONFIG_FILENAME = "scip_ecole_log_config.ini"
path_to_log_config_file = Path().cwd().joinpath(LOG_CONFIG_FILENAME)

try:
    logging.config.fileConfig(path_to_log_config_file)
except KeyError as err:
    print(f"Error. Configuration file `{LOG_CONFIG_FILENAME}` not found...")
    sys.exit(-1)
else:
    logger = logging.getLogger("sLogger")
