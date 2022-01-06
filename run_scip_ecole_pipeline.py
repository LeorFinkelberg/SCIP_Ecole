import os
import sys
import typing as t
from dataclasses import dataclass, field

import dotenv
import ecole
import yaml
from pathlib2 import Path, PosixPath

from scip_ecole_logger import logger


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
        logger.info(f"File `{path_to_settings_file}` has been read successfully!")

    return settings


# def scip_ecole_optimize():


def main():
    """
    Главная функция, запускающая цепочку вычислений
    на базе связки SCIP+Ecole
    """
    # Загрузить локальные переменные в текущее окружение
    dotenv.load_dotenv(".env")

    # Конфигурационный файл управляения связкой SCIP+Ecole
    SCIP_ECOLE_MODEL_CONFIG_FILENAME = os.getenv("SCIP_ECOLE_MODEL_CONFIG_FILENAME")
    path_to_scip_ecole_model_config_file = Path().cwd().joinpath(SCIP_ECOLE_MODEL_CONFIG_FILENAME)

    # Словарь параметров для управления связкой SCIP+Ecole
    config_params: dict = read_config_yaml_file(path_to_scip_ecole_model_config_file)

    # Путь до lp-файла математической постановки задачи
    path_to_lp_file: PosixPath = Path(config_params["path_to_lp_file"])
    # Путь до set-файла настроек решателя SCIP
    path_to_scip_solver_configs: PosixPath = Path(config_params["path_to_scip_solver_configs"])

    """
    try:
        model = ecole.scip.Model.from_file(path_to_lp_file)
    except ecole.core.scip.Exception as err:
        logger.error(f"{err}")
        sys.exit(-1)
    else:
        logger.info(f"File `{path_to_lp_file}` has been read successfully!")

    # Словарь начальных управляющих параметров решателя SCIP
    scip_settings: dict = read_scip_solver_settings_file(path_to_scip_solver_configs)
    model.set_params(scip_settings)
    """

    print(type(path_to_lp_file))
    # model.solve()


if __name__ == "__main__":
    main()
