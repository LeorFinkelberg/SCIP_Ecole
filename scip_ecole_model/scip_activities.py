import collections
import sys
import typing as t

import matplotlib.pyplot as plt
import pandas as pd
import pathlib2
import pyscipopt

from scip_ecole_model.parser import StatFileParser
from scip_ecole_model.scip_elems import SCIPAttributes
from scip_ecole_model.utils.scip_ecole_logger import logger


class SCIPActivitiesInTime:
    """
    Класс развертывания активностей элементов stat-файла во времени
    """

    def __init__(
        self,
        *,
        path_to_lp_file: pathlib2.Path,
        path_to_set_file: pathlib2.Path,
        path_to_stat_file: pathlib2.Path,
        time_limit: float,
        time_step: float,
        section_names: t.Tuple[str, ...],
    ):
        self.path_to_lp_file = path_to_lp_file
        self.path_to_set_file = path_to_set_file
        self.path_to_stat_file = path_to_stat_file
        self.time_limit = time_limit
        self.time_step = time_step
        self.section_names = section_names

        self._sections_and_section_names_to_list_rows = collections.defaultdict(list)

        model = pyscipopt.Model()
        try:
            model.readProblem(str(self.path_to_lp_file))
            model.readParams(str(self.path_to_set_file))
        except OSError as err:
            logger.error(f"{err}")
            sys.exit(-1)
        else:
            logger.info(
                f"Files '{self.path_to_lp_file}' and '{self.path_to_set_file}' was read successfully!"
            )

        self.count_of_frames = int(time_limit / time_step)

        for frame_number in range(0, self.count_of_frames):
            model.setParam(
                f"{SCIPAttributes.LIMITS_TIME}", (1 + frame_number) * time_step
            )

            logger.info(
                f"Problem was launched for calculation (frame #{frame_number + 1})"
            )
            model.optimize()
            if model.getStatus() == SCIPAttributes.STATUS_TIMELIMIT:
                prefix_stat_file: pathlib2.Path = self.path_to_stat_file.parents[0]
                stat_file_name: str = self.path_to_stat_file.name

                stat_file_name, stat_file_extension = stat_file_name.split(".")
                stat_file_name = (
                    f"{stat_file_name}_{frame_number + 1}.{stat_file_extension}"
                )
                path_to_stat_file = prefix_stat_file.joinpath(
                    pathlib2.Path(stat_file_name)
                )

                try:
                    model.writeStatistics(str(path_to_stat_file))
                    stat_file = StatFileParser(path_to_stat_file=path_to_stat_file)
                except FileNotFoundError as err:
                    logger.error(f"{err}")
                    sys.exit(-1)
                else:
                    logger.info(f"File '{path_to_stat_file}' was read successfully!")

                for section_name in section_names:
                    self._preprocessing_to_rolling_elem_activities_in_time(
                        stat_file=stat_file,
                        section_name=section_name,
                        frame_number=frame_number,
                    )

    def _preprocessing_to_rolling_elem_activities_in_time(
        self,
        *,
        stat_file: StatFileParser,
        section_name: str,
        frame_number: int,
    ) -> t.NoReturn:
        """
        Извлекает строку из соответствующей секции stat-файла
        по имени секции и имени элемента секции и помещает
        извлеченную строку-кадр в хранилище
        """
        section: pd.DataFrame = stat_file.get_section(section_name)
        section_elems: t.List[str] = section.index.to_list()

        for section_elem in section_elems:
            row_of_section: pd.DataFrame = section.loc[[section_elem]]
            row_of_section = row_of_section.reset_index()
            row_of_section["frame_number"] = frame_number
            row_of_section = row_of_section.rename(
                columns={section_name: "section_elem"}
            )

            self._sections_and_section_names_to_list_rows[
                f"{section_name}.{section_elem}"
            ].append(row_of_section)

    def get_rolling_elem_in_time(
        self,
        *,
        section_name: str,
        section_elem_name: str,
    ) -> pd.DataFrame:
        """
        Собирает развертку во времени для элемента секции
        """
        return (
            pd.concat(
                self._sections_and_section_names_to_list_rows[
                    f"{section_name}.{section_elem_name}"
                ]
            )
            .set_index("frame_number")
            .sort_index()
        )

    def plot(
        self,
        section_name: str,
        section_elem_name: str,
        path_to_save_fig: pathlib2.Path,
        figsize: t.Tuple[int, int] = (15, 10),
        save_fig: bool = False,
        dpi: int = 350,
    ) -> t.NoReturn:
        """
        Отрисовывает графики активности
        по заданной секции stat-файла
        """
        fig, ax = plt.subplots(figsize=figsize)

        self.get_rolling_elem_in_time(
            section_name=section_name, section_elem_name=section_elem_name
        ).plot(ax=ax, style="o")

        if save_fig:
            prefix_figures: pathlib2.Path = path_to_save_fig.parents[0]
            if not prefix_figures.exists():
                prefix_figures.mkdir()

            plt.savefig(path_to_save_fig, dpi=dpi)


if __name__ == "__main__":
    SECTION_NAMES = (
        "Constraints",
        "LP",
        "Propagators",
        "Conflict_Analysis",
        "Separators",
        "Primal_Heuristics",
    )
    activities_in_time = SCIPActivitiesInTime(
        path_to_lp_file=pathlib2.Path(
            "./input_for_model/planner_bin_from_scip_337_22.03.lp"
        ),
        path_to_set_file=pathlib2.Path("./input_for_model/scip.set"),
        path_to_stat_file=pathlib2.Path(
            "./output_from_model/337_bin_suppress_prime_heur.stat"
        ),
        time_limit=40 * 60,
        time_step=60,
        section_names=SECTION_NAMES,
    )

    activities_in_time.plot(
        section_name="LP",
        section_elem_name="dual_LP",
        path_to_save_fig=pathlib2.Path("./output_from_model/figures/activities.pdf"),
        save_fig=True,
    )
    """
    print(activities_in_time.get_rolling_elem_in_time(
        section_name="Constraints",
        section_elem_name="varbound"
    ))
    """
