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


def write_results_and_stats(
    problem_name: str,
    model: pyscipopt.scip.Model,
    stats_before_solving: t.NamedTuple,
    path_to_output_dir: PosixPath,
) -> t.NoReturn:
    """
    Записывает результаты поиска решения и статистику
    """
    obj_val: float = model.getObjVal()
    obj_sense: str = model.getObjectiveSense()
    gap: float = model.getGap()
    solving_time: float = model.getSolvingTime()
    status: str = model.getStatus()
    n_sols: int = model.getNSols()
    n_best_sols: int = model.getNBestSolsFound()

    n_vars: int = stats_before_solving.n_vars
    n_bin_vars: int = stats_before_solving.n_bin_vars
    n_int_vars: int = stats_before_solving.n_int_vars
    n_cont_vars: int = n_vars - n_bin_vars - n_int_vars
    n_conss: int = stats_before_solving.n_conss

    n_vars_after_presolving: int = model.getNVars()
    n_bin_vars_after_presolving: int = model.getNBinVars()
    n_int_vars_after_presolving: int = model.getNIntVars()
    n_cont_vars_after_presolving: int = (
        n_vars_after_presolving
        - n_bin_vars_after_presolving
        - n_int_vars_after_presolving
    )
    n_conss_after_presolving: int = model.getNConss()

    logger.info(
        f"\n\tSummary:\n"
        f"\t- Problem name (sense): {problem_name} ({obj_sense})\n"
        f"\t- N Vars: {n_vars} (after presolving {n_vars - n_vars_after_presolving} vars was deleted)\n"
        f"\t\t* N Bin Vars: {n_bin_vars} (after presolving {n_bin_vars_after_presolving})\n"
        f"\t\t* N Int Vars: {n_int_vars} (after presolving {n_int_vars_after_presolving})\n"
        f"\t\t* N Cont Vars: {n_cont_vars} (after presolving {n_cont_vars_after_presolving})\n"
        f"\t- N Conss: {n_conss} (after presolving {n_conss - n_conss_after_presolving} conss was deleted)\n"
        f"\n\tResults:\n"
        f"\t- N Sols / N Best sols: {n_sols} / {n_best_sols}\n"
        f"\t- Objective value [{status}]: {obj_val:.8g}\n"
        f"\t- Gap: {gap * 100:.3g}%\n"
        f"\t- Solving time: {solving_time / 60:.2g} min"
    )

    path_to_output_dir = Path().cwd().joinpath(path_to_output_dir)
    best_sol_filename = (
        f"{problem_name}_{n_vars}_{n_bin_vars}_{n_int_vars}_{n_conss}.sol"
    )
    stats_filename = f"{problem_name}_{n_vars}_{n_bin_vars}_{n_int_vars}_{n_conss}.stats"

    model.writeBestSol(path_to_output_dir.joinpath(best_sol_filename), write_zeros=True)
    model.writeStatistics(path_to_output_dir.joinpath(stats_filename))


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
