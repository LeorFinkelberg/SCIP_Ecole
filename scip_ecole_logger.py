import logging.config
import os
import sys

import dotenv
from pathlib2 import Path

dotenv.load_dotenv(".env")
LOG_CONFIG_FILENAME = os.getenv("LOG_CONFIG_FILENAME")
path_to_log_config_file = Path().cwd().joinpath(LOG_CONFIG_FILENAME)

try:
    logging.config.fileConfig(path_to_log_config_file)
except KeyError as err:
    print(f"Error. Configuration file `{LOG_CONFIG_FILENAME}` not found...")
    sys.exit(-1)
else:
    logger = logging.getLogger("sLogger")
