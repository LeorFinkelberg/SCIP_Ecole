import logging
import sys
import typing as t
from collections import namedtuple

import pyscipopt
import yaml
from pathlib2 import Path, PosixPath

from scip_ecole_model.scip_ecole_logger import logger


def read_config_yaml_file(path_to_config_file: PosixPath) -> dict:
    """
    Читает конфигурационный файл
    управления связкой SCIP+Ecole
    """
    try:
        with open(path_to_config_file) as fo:
            config_params = yaml.safe_load(fo)
    except FileNotFoundError as err:
        logger.error(f"{err}")
        sys.exit(-1)
    else:
        logger.info(f"File `{path_to_config_file.name}` has been read successfully!")

    return config_params


def read_scip_solver_settings_file(path_to_settings_file: PosixPath) -> dict:
    """
    Читает файл настроек решателя SCIP
    """
    settings: t.Dict[str, t.Union[str, int, float, bool]] = {}
    try:
        with open(path_to_settings_file, mode="r", encoding="utf-8") as fo:
            try:
                for line in fo:
                    line = line.strip()
                    if line.startswith("#") or not line:
                        continue

                    param, value = line.split("=")
                    param = param.strip()
                    value = value.lower().strip()

                    if value == "true":
                        value = True
                    elif value == "false":
                        value = False
                    elif value.isnumeric():
                        value = float(value)
                    elif value.startswith("-"):
                        value = float(value)
                    elif ("." in value) or ("e" in value):
                        value = float(value)
                    elif value.isalpha():
                        value = str(value)
                    else:
                        raise ValueError(
                            f"Incorrect value `{value}` ({param}: {value}) "
                            f"in `{path_to_settings_file}`..."
                        )

                    settings[param] = value
            except ValueError as err:
                logger.error(f"{err}")
                sys.exit(-1)
    except FileNotFoundError as err:
        logger.error(f"{err}")
        sys.exit(-1)
    else:
        params_info = f"File `{path_to_settings_file}` has been read successfully!"
        params_info += "\n\tSCIP settings:\n"
        for param_name, value in settings.items():
            params_info += f"\t\t{param_name} = {value}\n"
        logger.info(params_info)

    return settings


def get_stats_before_solving(
    path_to_lp_file: PosixPath, logger: logging.Logger
) -> t.NamedTuple:
    """
    Собирает статистику о задаче до запуска решения
    """
    model = pyscipopt.scip.Model()
    try:
        model.readProblem(path_to_lp_file)
    except OSError as err:
        logger.error(f"{err}")
        sys.exit(-1)
    n_vars: int = model.getNVars()
    n_bin_vars: int = model.getNBinVars()
    n_int_vars: int = model.getNIntVars()
    n_conss: int = model.getNConss()

    model_stats = namedtuple(
        "model_stats", ["n_vars", "n_bin_vars", "n_int_vars", "n_conss"]
    )
    model_stats.n_vars = n_vars
    model_stats.n_bin_vars = n_bin_vars
    model_stats.n_int_vars = n_int_vars
    model_stats.n_conss = n_conss

    return model_stats
