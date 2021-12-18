import logging.config

from pathlib2 import Path

LOG_CONFIG_FILE_NAME = "scip_ecole_logging.ini"
path_to_log_config_file = Path().cwd().joinpath(LOG_CONFIG_FILE_NAME)

logging.config.fileConfig(path_to_log_config_file)
logger = logging.getLogger("sLogger")
