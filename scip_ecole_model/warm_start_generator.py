import os
import sys
import typing as t

import dotenv
import pyscipopt
from pathlib2 import Path, PosixPath

from scip_ecole_model.auxiliary_functions import *
from scip_ecole_model.scip_ecole_logger import logger


def read_sol_file(path_to_sol_file: PosixPath) -> dict:
    """
    Преобразует sol-файл в словарь пар "имя_переменной-значение"
    """
    sol_file_parsed = {}

    try:
        with open(path_to_sol_file) as sol_file:
            for line in sol_file:
                if line.startswith("#") or "objective" in line:
                    continue
                key, value = line.split()[:2]
                sol_file_parsed[key] = float(value)
    except FileNotFoundError as err:
        logger.error(f"{err}")
        sys.exit(-1)
    else:
        logger.info(f"File `{path_to_sol_file.name}` has been read successfully!")

    return sol_file_parsed


def gen_warm_start_wo_zeros_vals(
    path_to_lp_file: PosixPath,
    path_to_sol_file: PosixPath,
) -> t.NoReturn:
    """
    Удаляет переменные, которые в "теплом" старте
    были инициализированы
    нулями (не зависимо от типа переменных)
    """
    dotenv.load_dotenv(".env")

    model = pyscipopt.Model()
    model.readProblem(str(path_to_lp_file))
    warm_start: pyscipopt.scip.Solution = model.readProblem(str(path_to_sol_file))
    model.addSol(warm_start)
    sol: pyscipopt.scip.Solution = model.getSols()[0]

    for var in model.getVars():
        if model.getSolvingTime(sol, var) == 0.0:
            model.delVar(var)
            logger.info(f"Var {var} has been deleted...")

    SCIP_ECOLE_MODEL_CONFIG_FILENAME = os.getenv("SCIP_ECOLE_MODEL_CONFIG_FILENAME")
    path_to_scip_ecole_model_config_file = (
        Path().cwd().joinpath(SCIP_ECOLE_MODEL_CONFIG_FILENAME)
    )
    config_params: dict = read_config_yaml_file(path_to_scip_ecole_model_config_file)
    path_to_output_dir: PosixPath = Path(config_params["path_to_output_dir"])

    model.writeProblem(
        path_to_output_dir.joinpath(f"{path_to_lp_file.name}_wo_zeros_vals")
    )
