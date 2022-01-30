import os
import sys
import typing as t

import dotenv
import ecole
import pyscipopt
from pathlib2 import Path, PosixPath

from scip_ecole_model.auxiliary_functions import *
from scip_ecole_model.envs import SimpleBranchingEnv
from scip_ecole_model.scip_ecole_logger import logger


def scip_optimize(
    env: t.Union[
        ecole.environment.Branching,
        ecole.environment.Configuring,
    ],
    path_to_lp_file: PosixPath,
    path_to_warm_start_file: PosixPath,
    use_warm_start: bool = False,
) -> pyscipopt.scip.Model:
    """
    Запускает процесс поиска решения
    только с помощью SCIP
    """
    model_scip = pyscipopt.scip.Model()
    # Прочитать файл математической постановки
    try:
        model_scip.readProblem(str(path_to_lp_file))
    except OSError as err:
        logger.error(f"{err}")
        sys.exit(-1)
    else:
        logger.info(f"File `{path_to_lp_file.name}` has been read successfully!")
    scip_params = env.scip_params
    model_scip.setParams(scip_params)

    if use_warm_start:
        # Прочитать файл стартового решения
        try:
            warm_start_for_SCIP: pyscipopt.scip.Solution = model_scip.readSolFile(
                str(path_to_warm_start_file)
            )
        except OSError as err:
            logger.error(f"{err}")
            sys.exit(-1)
        else:
            logger.info(
                f"File `{path_to_warm_start_file.name}` has been read successfully!"
            )

            # Добавить решение для 'теплого' старта
            model_scip.addSol(warm_start_for_SCIP)

            model_scip.optimize()

    return model_scip


def scip_ecole_optimize(
    env: t.Union[
        ecole.environment.Branching,
        ecole.environment.Configuring,
    ],
    path_to_lp_file: PosixPath,
    path_to_warm_start_file: PosixPath,
    use_warm_start: bool = False,
) -> ecole.core.scip.Model:
    """
    Запускает процесс поиска решения с помощью SCIP+Ecole
    """
    env.seed(42)
    nb_nodes, time = 0, 0

    if use_warm_start:
        model_scip = pyscipopt.scip.Model()
        # Прочитать файлы математической постановки и стартового решения
        try:
            model_scip.readProblem(str(path_to_lp_file))
        except OSError as err:
            logger.error(f"{err}")
            sys.exit(-1)
        else:
            logger.info(f"File `{path_to_lp_file.name}` has been read successfully!")

        try:
            warm_start_for_SCIP: pyscipopt.scip.Solution = model_scip.readSolFile(
                str(path_to_warm_start_file)
            )
        except OSError as err:
            logger.error(f"{err}")
            sys.exit(-1)
        else:
            logger.info(f"File `{path_to_warm_start_file}` has been read successfully!")

        scip_params = env.scip_params
        model_scip.setParams(scip_params)
        # Добавить решение для 'теплого' старта
        model_scip.addSol(warm_start_for_SCIP)
        model_ecole = ecole.scip.Model.from_pyscipopt(model_scip)
    else:
        model_ecole = str(path_to_lp_file)

    logger.info("Reset environment ...")
    obs, action_set, reward, done, info = env.reset(model_ecole)

    msg = (
        "\n\tNew step in environment [iter={}]\n"
        "\taction_set: {}\n"
        "\treward: {}\n"
        "\tinfo: {}\n"
        "\tdone: {}\n"
    )

    count = 0
    while not done:
        logger.info(msg.format(count, action_set, reward, info, done))
        obs, action_set, reward, done, info = env.step(action_set[0])

        nb_nodes += info["nb_nodes"]
        time += info["time"]
        count += 1

    return env.model.as_pyscipopt()


def main():
    """
    Главная функция, запускающая цепочку вычислений
    на базе связки SCIP+Ecole
    """
    logger.info("Procedure for finding solution with `SCIP+Ecole` has been started ...")
    # Загрузить локальные переменные в текущее окружение
    dotenv.load_dotenv(".env")

    # Конфигурационный файл управляения связкой SCIP+Ecole
    SCIP_ECOLE_MODEL_CONFIG_FILENAME = os.getenv("SCIP_ECOLE_MODEL_CONFIG_FILENAME")
    path_to_scip_ecole_model_config_file = (
        Path().cwd().joinpath(SCIP_ECOLE_MODEL_CONFIG_FILENAME)
    )

    # Словарь параметров для управления связкой SCIP+Ecole
    config_params: dict = read_config_yaml_file(path_to_scip_ecole_model_config_file)

    # Наименование задачи
    problem_name: str = config_params["problem_name"]
    # Флаг использования только ресурсов решателя SCIP (без Ecole)
    use_scip_ecole: bool = config_params["use_scip_ecole"]
    # Путь до lp-файла математической постановки задачи
    path_to_lp_file: PosixPath = Path(config_params["path_to_lp_file"])
    # Путь до set-файла настроек решателя SCIP
    path_to_scip_solver_configs: PosixPath = Path(
        config_params["path_to_scip_solver_configs"]
    )
    # Путь до директории с результатами поиска решения
    path_to_output_dir: PosixPath = Path(config_params["path_to_output_dir"])
    # Путь до sol-файла 'теплого' старта решателя SCIP
    path_to_warm_start_file: PosixPath = Path(config_params["path_to_warm_start_file"])
    # Флаг использования теплого старта
    use_warm_start: bool = config_params["use_warm_start"]

    # Словарь начальных управляющих параметров решателя SCIP
    scip_params: dict = read_scip_solver_settings_file(path_to_scip_solver_configs)

    # Собрать статистику о задаче до запуска решения
    stats_before_solving: t.NamedTuple = get_stats_before_solving(
        path_to_lp_file=path_to_lp_file
    )

    # Создать экземпляр окружения
    env = SimpleBranchingEnv(
        observation_function=ecole.observation.Pseudocosts(),
        reward_function=ecole.reward.SolvingTime(),
        information_function={
            "nb_nodes": ecole.reward.NNodes().cumsum(),
            "time": ecole.reward.SolvingTime().cumsum(),
        },
        scip_params=scip_params,
    ).create_env()

    # Запустить процедуру поиска решения
    if use_scip_ecole:
        # Использовать связку SCIP+Ecole
        logger.info("SCIP+Ecole bundle is used.")
        model = scip_ecole_optimize(
            env=env,
            path_to_lp_file=path_to_lp_file,
            path_to_warm_start_file=path_to_warm_start_file,
            use_warm_start=use_warm_start,
        )
    else:
        # Использовать только решатель SCIP
        logger.info("Only SCIP is used.")
        model = scip_optimize(
            env=env,
            path_to_lp_file=path_to_lp_file,
            path_to_warm_start_file=path_to_warm_start_file,
            use_warm_start=use_warm_start,
        )

    # Записать статистику и резульаты поиска решения
    write_results_and_stats(
        problem_name=problem_name,
        model=model,
        stats_before_solving=stats_before_solving,
        path_to_output_dir=path_to_output_dir,
    )


if __name__ == "__main__":
    main()
