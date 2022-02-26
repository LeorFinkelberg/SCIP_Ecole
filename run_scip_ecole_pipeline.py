import os

import dotenv
import ecole
from pathlib2 import Path, PosixPath

from scip_ecole_model.auxiliary_functions import *
from scip_ecole_model.envs import SimpleBranchingEnv
from scip_ecole_model.optimize import scip_ecole_optimize, scip_optimize
from scip_ecole_model.scip_ecole_logger import logger


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
        path_to_lp_file=path_to_lp_file,
        logger=logger,
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
            logger=logger,
        )

    # Записать статистику и резульаты поиска решения
    write_results_and_stats(
        problem_name=problem_name,
        model=model,
        stats_before_solving=stats_before_solving,
        path_to_output_dir=path_to_output_dir,
        logger=logger,
    )


if __name__ == "__main__":
    main()
