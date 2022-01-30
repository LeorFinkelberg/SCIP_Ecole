import os
import sys
import typing as t

import click
import dotenv
import numpy as np
import pathlib2
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


@click.command()
@click.option(
    "--path-to-lp-file",
    required=True,
    type=click.Path(
        exists=True,
        file_okay=True,
        readable=True,
        path_type=pathlib2.Path,
    ),
    help="Путь до lp-файла",
)
@click.option(
    "--path-to-sol-file",
    required=True,
    type=click.Path(
        exists=True,
        path_type=pathlib2.Path,
    ),
    help="Путь до sol-файла",
)
@click.option(
    "--path-to-input-dir",
    required=True,
    type=click.Path(exists=True, path_type=pathlib2.Path),
    default=Path("./input_for_model"),
    help="Путь до директории входнных модели",
)
def gen_warm_start_wo_zeros_vals(
    path_to_lp_file: PosixPath,
    path_to_sol_file: PosixPath,
    path_to_input_dir: PosixPath,
) -> t.NoReturn:
    """
    Удаляет переменные, которые в "теплом" старте
    были инициализированы
    нулями (не зависимо от типа переменных)
    """
    dotenv.load_dotenv(".env")

    model = pyscipopt.Model()
    try:
        model.readProblem(str(path_to_lp_file))
        warm_start: pyscipopt.scip.Solution = model.readSolFile(str(path_to_sol_file))
    except OSError as err:
        logger.error(f"{err}")
        sys.exit(-1)
    else:
        logger.info(f"File `{path_to_lp_file.name}` has been read successfully!")
        model.addSol(warm_start)

        sol: pyscipopt.scip.Solution = model.getSols()[0]

    for var in model.getVars():
        if np.round(model.getSolVal(sol, var)) == 0.0:
            model.delVar(var)

    model.writeProblem(
        path_to_input_dir.joinpath(
            Path(f"{path_to_lp_file.name.split('.')[0]}_wo_zeros_vals.lp")
        )
    )


if __name__ == "__main__":
    gen_warm_start_wo_zeros_vals()
