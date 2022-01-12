import os
import sys
import typing as t
from collections import namedtuple

import dotenv
import ecole
import pyscipopt
import yaml
from pathlib2 import Path, PosixPath

from scip_ecole_model.envs import SimpleBranchingEnv
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
    model_scip.readProblem(str(path_to_lp_file))
    scip_params = env.scip_params
    model_scip.setParams(scip_params)

    if use_warm_start:
        # Прочитать файл стартового решения
        try:
            warm_start_for_SCIP: pyscipopt.scip.Solution = model_scip.readSolFile(
                str(path_to_warm_start_file)
            )
            # Добавить решение для 'теплого' старта
            model_scip.addSol(warm_start_for_SCIP)
        except OSError as err:
            logger.error(f"{err}")
            sys.exit(-1)

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
            warm_start_for_SCIP: pyscipopt.scip.Solution = model_scip.readSolFile(
                str(path_to_warm_start_file)
            )
        except OSError as err:
            logger.error(f"{err}")
            sys.exit(-1)

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


def get_stats_before_solving(path_to_lp_file: PosixPath) -> t.NamedTuple:
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

    logger.info(
        f"\n\tSummary:\n"
        f"\t- Problem name (sense): {problem_name} ({obj_sense})\n"
        f"\t- N Vars: {n_vars}\n"
        f"\t\t* N Bin Vars: {n_bin_vars}\n"
        f"\t\t* N Int Vars: {n_int_vars}\n"
        f"\t\t* N Cont Vars: {n_cont_vars}\n"
        f"\t- N Conss: {n_conss}\n"
        f"\n\tResults:\n"
        f"\t- N Sols / N Best sols: {n_sols} / {n_best_sols}\n"
        f"\t- Objective value [{status}]: {obj_val:.8g}\n"
        f"\t- Gap: {gap:.3g}\n"
        f"\t- Solving time: {solving_time / 60:.2g} min"
    )

    path_to_output_dir = Path().cwd().joinpath(path_to_output_dir)
    best_sol_filename = (
        f"{problem_name}_{n_vars}_{n_bin_vars}_{n_int_vars}_{n_conss}.sol"
    )
    stats_filename = f"{problem_name}_{n_vars}_{n_bin_vars}_{n_int_vars}_{n_conss}.stats"

    model.writeBestSol(path_to_output_dir.joinpath(best_sol_filename))
    model.writeStatistics(path_to_output_dir.joinpath(stats_filename))


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
        model = scip_ecole_optimize(
            env=env,
            path_to_lp_file=path_to_lp_file,
            path_to_warm_start_file=path_to_warm_start_file,
            use_warm_start=use_warm_start,
        )
    else:
        # Использовать только решатель SCIP
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
