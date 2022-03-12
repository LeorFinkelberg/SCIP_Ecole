import logging
import sys
import typing as t
from collections import namedtuple

import pyscipopt
import yaml
from pathlib2 import Path, PosixPath

from scip_ecole_model.utils.scip_ecole_logger import logger


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
        for idx, (param_name, value) in enumerate(settings.items()):
            params_info += f"\t\t{idx+1}: {param_name} = {value}\n"
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


def write_results_and_stats(
    problem_name: str,
    model: pyscipopt.scip.Model,
    stats_before_solving: t.NamedTuple,
    path_to_output_dir: PosixPath,
    logger: logging.Logger,
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
