import logging
import sys
import typing as t

import ecole
import pyscipopt
from pathlib2 import PosixPath


def scip_optimize(
    env: t.Union[
        ecole.environment.Branching,
        ecole.environment.Configuring,
    ],
    path_to_lp_file: PosixPath,
    path_to_warm_start_file: PosixPath,
    logger: logging.Logger,
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
    logger: logging.Logger,
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
    count = 0
    if env.__class__.__name__ == "Branching":
        obs, action_set, reward, done, info = env.reset(model_ecole)

        msg = (
            "\n\tNew step in environment [iter={}]\n"
            "\taction_set: {}\n"
            "\treward: {}\n"
            "\tinfo: {}\n"
            "\tdone: {}\n"
        )

        while not done:
            logger.info(msg.format(count, action_set, reward, info, done))
            obs, action_set, reward, done, info = env.step(action_set[0])

            nb_nodes += info["nb_nodes"]
            time += info["time"]
            count += 1
    elif env.__class__.__name__ == "PrimalSearchDynamics":
        done, action_set = env.reset_dynamics(model_ecole)

        msg = (
            "\n\tNew step in environment [iter={}]\n" "\taction_set: {}\n" "\tdone: {}\n"
        )

        while not done:
            logger.info(msg.format(count, action_set, done))
            done, action_set = env.step_dynamics(model_ecole, action_set[0])
            count += 1

    return env.model.as_pyscipopt()
