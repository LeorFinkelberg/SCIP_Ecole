import os
import sys
import typing as t

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


def scip_ecole_optimize(path_to_lp_file: PosixPath, scip_params: dict) -> ecole.core.scip.Model:
    """
    Запускает процесс поиска решения
    """
    env = ecole.environment.Branching(
        scip_params=scip_params,
        observation_function=ecole.observation.MilpBipartite(),
        reward_function=ecole.reward.NNodes(),
        information_function={
            "nb_nodes": ecole.reward.NNodes().cumsum(),
            "time": ecole.reward.SolvingTime().cumsum(),
        },
    )
    logger.info("Reset environment ...")
    nb_nodes, time = 0, 0
    obs, action_set, reward, done, info = env.reset(str(path_to_lp_file))
    print(f"After reset: {action_set}, {reward}, {done}, {info}")

    while not done:
        logger.info("New step in environment ...")
        obs, action_set, reward, done, info = env.step(action_set[0])
        print(f"In while-ecole loop: {obs}, {action_set}, {reward}, {done}, {info}")

        nb_nodes += info["nb_nodes"]
        time += info["time"]

    return env.model.as_pyscipopt()


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

    # Словарь начальных управляющих параметров решателя SCIP
    scip_params: dict = read_scip_solver_settings_file(path_to_scip_solver_configs)
    model = scip_ecole_optimize(path_to_lp_file, scip_params=scip_params)


if __name__ == "__main__":
    main()
