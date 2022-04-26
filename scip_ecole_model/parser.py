import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn
import seaborn as sns

sns.set_theme()
import collections
import re
import typing as t
from dataclasses import dataclass

import pathlib2
from pathlib2 import Path


class InvalidSectionError(Exception):
    """
    Исключение поднимается при попытке представления
    нетабличной секции в виде табличной абстракции
    """

    pass


@dataclass(frozen=True)
class ServiceAttributes:
    """
    Класс вспомогательных аттрибутов
    """

    _INVALID_SECTIONS = (
        "SCIP_Status",
        "Total_Time",
        "Original_Problem",
        "Presolved_Problem",
        "Pricers",
        "B&B_Tree",
        "Estim._Tree_Size",
        "Estimation_Tree",
        "Root_Node",
        "Integrals",
    )

    _ONE_BLANK = " " * 1
    _TWO_BLANK = " " * 2
    _SUB_STRING_FOR_DEL_CONFLICT_ANALYSIS = _ONE_BLANK * 3 + "(pool size: [--,--])"
    _SUB_STRING_FOR_DEL_SEPARATORS_CUT_POOL = (
        _ONE_BLANK * 4 + "(maximal pool size: 8995)"
    )

    _CONFLICT_ANALYSIS = "Conflict_Analysis"
    _SEPARATORS_CUT_POOL = "Separators.cut_pool"
    _LP_PRIMAL_LP = "LP.primal_LP"
    _LP_DUAL_LP = "LP.dual_LP"
    _LP_LEX_DUAL_LP = "LP.lex_dual_LP"
    _LP_BARRIER_LP = "LP.barrier_LP"
    _LP_RESOLVE_INSTABLE = "LP.resolve_instable"
    _LP_DIVING_PROBING_LP = "LP.diving/probing_LP"
    _LP_AT_ROOT_NODE = "LP.(at_root_node)"
    _LP_CONFLICT_ANALYSIS = "LP.conflict_analysis"
    _ESTIMATIONS_GAP = "Estimations.gap"
    _ESTIMATIONS_TREE_WEIGHT = "Estimations.tree-weight"
    _ESTIMATIONS_LEAF_FREQUENCY = "Estimations.leaf-frequency"
    _ESTIMATIONS_SSG = "Estimations.ssg"
    _ESTIMATIONS_OPEN_NODES = "Estimations.open-nodes"
    _SOLUTION_SOLUTIONS_FOUND = "Solution.First_Solution"

    _DIVING_SINGLE = "Diving_(single)"
    _DIVING_ADAPTIVE = "Diving_(adaptive)"
    _LP_ITER_WITH_WHITESPACE = "LP Iter"
    _LP_ITER_WO_WHITESPACE = "LP_Iter"

    _NUM_COLS_PRESOLVERS = 12
    _NUM_COLS_CONSTRAINTS = 15
    _NUM_COLS_CONSTRAINTS_TIMINGS = 10
    _NUM_COLS_PROPAGATORS = 4
    _NUM_COLS_PROPAGATORS_TIMINGS = 6
    _NUM_COLS_CONFLICT_ANALYSIS = 11
    _NUM_COLS_SEPARATORS = 8
    _NUM_COLS_PRIMAL_HEURISTICS = 5
    _NUM_COLS_DIVING_SINGLE = 13
    _NUM_COLS_DIVING_ADAPTIVE = 13
    _NUM_COLS_NEIGHBORHOODS = 18


class StatFileParser:
    """
    Парсит stat-файл, подготовленный решателем SCIP
    ...
    SCIP> write stats file_name.stat
    """

    def __init__(
        self,
        *,
        path_to_stat_file: t.Union[str, pathlib2.Path],
        main_delimiter: str = ":",
    ) -> t.NoReturn:
        self.path_to_stat_file = path_to_stat_file
        self.main_delimiter = main_delimiter
        self._structure_of_doc = collections.OrderedDict()

        with open(self.path_to_stat_file, encoding="utf-8") as stat_file:
            for line in stat_file:
                # Headers
                if not line.startswith(ServiceAttributes._TWO_BLANK):
                    header, right_part_of_separtor = line.split(
                        self.main_delimiter, maxsplit=1
                    )
                    header = header.strip().replace(ServiceAttributes._ONE_BLANK, "_")

                    if header == ServiceAttributes._CONFLICT_ANALYSIS:
                        right_part_of_separtor = self._regex_delete_sub_string(
                            value=right_part_of_separtor,
                            sub_string_for_del=ServiceAttributes._SUB_STRING_FOR_DEL_CONFLICT_ANALYSIS,
                        )
                        right_part_of_separtor = right_part_of_separtor.replace(
                            ServiceAttributes._LP_ITER_WITH_WHITESPACE,
                            ServiceAttributes._LP_ITER_WO_WHITESPACE,
                        )
                        self._structure_of_doc[header] = right_part_of_separtor
                    elif header == ServiceAttributes._DIVING_SINGLE:
                        right_part_of_separtor = right_part_of_separtor.replace(
                            ServiceAttributes._LP_ITER_WITH_WHITESPACE,
                            ServiceAttributes._LP_ITER_WO_WHITESPACE,
                        )
                        self._structure_of_doc[header] = right_part_of_separtor.strip()
                    elif header == ServiceAttributes._DIVING_ADAPTIVE:
                        self._structure_of_doc[header] = right_part_of_separtor.replace(
                            ServiceAttributes._LP_ITER_WITH_WHITESPACE,
                            ServiceAttributes._LP_ITER_WO_WHITESPACE,
                        )
                    else:
                        self._structure_of_doc[header] = right_part_of_separtor.strip()
                # Subheaders
                else:
                    sub_header, value = line.strip().split(
                        self.main_delimiter, maxsplit=1
                    )
                    header = list(self._structure_of_doc.keys())[-1].split(
                        ".", maxsplit=1
                    )[0]
                    sub_header = sub_header.strip().replace(
                        ServiceAttributes._ONE_BLANK, "_"
                    )
                    key = f"{header}.{sub_header}"

                    if key in (
                        ServiceAttributes._LP_PRIMAL_LP,
                        ServiceAttributes._LP_DUAL_LP,
                        ServiceAttributes._LP_BARRIER_LP,
                    ):
                        self._append_value(key, value)
                    elif key in (
                        ServiceAttributes._ESTIMATIONS_GAP,
                        ServiceAttributes._ESTIMATIONS_TREE_WEIGHT,
                        ServiceAttributes._ESTIMATIONS_LEAF_FREQUENCY,
                        ServiceAttributes._ESTIMATIONS_SSG,
                        ServiceAttributes._ESTIMATIONS_OPEN_NODES,
                    ):
                        self._append_insert_value(key, value)
                    elif key in (
                        ServiceAttributes._LP_LEX_DUAL_LP,
                        ServiceAttributes._LP_RESOLVE_INSTABLE,
                        ServiceAttributes._LP_DIVING_PROBING_LP,
                        ServiceAttributes._LP_AT_ROOT_NODE,
                        ServiceAttributes._LP_CONFLICT_ANALYSIS,
                    ):
                        self._extend_value(key, value)
                    elif key == ServiceAttributes._SEPARATORS_CUT_POOL:
                        values: t.List[str] = self._regex_delete_sub_string(
                            value=value,
                            sub_string_for_del=ServiceAttributes._SUB_STRING_FOR_DEL_SEPARATORS_CUT_POOL,
                        ).split()
                        values.insert(1, "-")
                        self._structure_of_doc[key] = (
                            ServiceAttributes._ONE_BLANK
                        ).join(values)
                    else:
                        self._structure_of_doc[key] = value.strip()

        for key, value in self._structure_of_doc.items():
            # The order of placement of conditions is important!!!
            if self._regex_extract_float_number(value):
                self._structure_of_doc[key] = float(
                    self._regex_extract_float_number(value)[0]
                )
            elif self._regex_extract_simple_int_float_number(value):
                self._structure_of_doc[key] = float(
                    self._regex_extract_simple_int_float_number(value)[0][0]
                )
            elif self._regex_extract_vars_stats(value):
                (vars_, bins, ints, impl_ints, conts) = self._regex_extract_vars_stats(
                    value
                )[0]
                self._structure_of_doc[key] = {
                    "vars": int(vars_),
                    "bins": int(bins),
                    "ints": int(ints),
                    "impl_ints": int(impl_ints),
                    "conts": int(conts),
                }
            elif self._regex_extract_nodes(value):
                (nodes, internal, leaves) = self._regex_extract_nodes(value)[0]
                self._structure_of_doc[key] = {
                    "nodes": int(nodes),
                    "internal": int(internal),
                    "leaves": int(leaves),
                }
            elif self._regex_extract_repropagations(value):
                (
                    repropagations,
                    domain_reductions,
                    cutoffs,
                ) = self._regex_extract_repropagations(value)[0]
                self._structure_of_doc[key] = {
                    "repropagations": int(repropagations),
                    "domain_reductions": int(domain_reductions),
                    "cutoffs": cutoffs,
                }
            elif self._regex_extract_estimation_tree(value):
                (
                    et_nodes,
                    et_visited,
                    et_internal,
                    et_leaves,
                    et_open,
                ) = self._regex_extract_estimation_tree(value)[0]
                self._structure_of_doc[key] = {
                    "et_nodes": int(et_nodes),
                    "et_visited": int(et_visited),
                    "et_leaves": int(et_leaves),
                    "et_open": int(et_open),
                }
            elif self._regex_extract_sol_sols_found(value):
                (
                    first_sol,
                    run,
                    after_nodes,
                    seconds,
                    depth,
                    found_by_heur,
                ) = self._regex_extract_sol_sols_found(value)[0]
                self._structure_of_doc[key] = {
                    "first_sol": float(first_sol),
                    "run": int(run),
                    "after_nodes": int(after_nodes),
                    "seconds": float(seconds),
                    "depth": int(depth),
                    "found_by_heur": found_by_heur,
                }
            elif self._regex_extract_conss_stats(value):
                self._structure_of_doc[key] = int(
                    self._regex_extract_conss_stats(value)[0]
                )
            elif self._regex_extract_gap(value):
                self._structure_of_doc[key] = float(self._regex_extract_gap(value)[0])
            elif len(value.split()) in (
                ServiceAttributes._NUM_COLS_PRESOLVERS,
                ServiceAttributes._NUM_COLS_CONSTRAINTS,
                ServiceAttributes._NUM_COLS_CONSTRAINTS_TIMINGS,
                ServiceAttributes._NUM_COLS_PROPAGATORS,
                ServiceAttributes._NUM_COLS_PROPAGATORS_TIMINGS,
                ServiceAttributes._NUM_COLS_CONFLICT_ANALYSIS,
                ServiceAttributes._NUM_COLS_SEPARATORS,
                ServiceAttributes._NUM_COLS_PRIMAL_HEURISTICS,
                ServiceAttributes._NUM_COLS_DIVING_SINGLE,
                ServiceAttributes._NUM_COLS_DIVING_ADAPTIVE,
                ServiceAttributes._NUM_COLS_NEIGHBORHOODS,
            ):
                self._structure_of_doc[key] = [
                    (
                        self._regex_extract_int_number_wo_plus(elem)[0]
                        if self._regex_extract_int_number_wo_plus(elem)
                        else elem
                    )
                    for elem in value.split()
                ]
            else:
                continue

    @property
    def get_keys(self) -> t.List[str]:
        return list(self._structure_of_doc.keys())

    @property
    def get_invalid_sections(self) -> t.Tuple[str, ...]:
        """
        Возвращает имена секций, которые
        не могут быть представлены табличными абстакциями
        """
        return ServiceAttributes._INVALID_SECTIONS

    def get_section(self, section_name: str) -> pd.DataFrame:
        """
        Читает раздел stats-файла как таблицу
        """
        if section_name in ServiceAttributes._INVALID_SECTIONS:
            raise InvalidSectionError(
                "Oops. This section cannot be read as a table!\n"
                "See the list of invalid section names: \n"
                ">>> StatFileParser(path_to_stat_file='...').invalid_sections"
            )

        columns: t.List[str] = self._structure_of_doc[section_name]

        section = pd.DataFrame.from_records(
            data=[
                value
                for key, value in self._structure_of_doc.items()
                if f"{section_name}." in key
            ],
            index=[
                key.split(".")[1]
                for key, value in self._structure_of_doc.items()
                if f"{section_name}." in key
            ],
            columns=self._structure_of_doc[section_name],
        )
        section.index.name = section_name

        return section.replace(to_replace="-", value=np.nan).fillna(0).astype(np.float64)

    def _regex_extract_float_number(self, value: str) -> list:
        """
        Извлекает вещественное число
        из строки с 'мусорным' хвостом
        """
        return re.compile(r"^(\d+[.]\d+)\s\(.*$").findall(value)

    def _regex_extract_simple_int_float_number(self, value: str) -> list:
        """
        Извлекает целое или вещественное число
        """
        return re.compile(r"^(\d+([.]\d+)?)$").findall(value)

    def _regex_extract_int_number_wo_plus(self, value: str) -> list:
        """
        Извлекает из 'числовой' строки целое число
        без следующего за ним символа '+'
        """
        return re.compile(r"^(\d+)\+$").findall(value)

    def _regex_extract_vars_stats(self, value: str) -> list:
        """
        Извлекает:
        - общее количество переменных,
        - количество бинарных переменных,
        - количество целочисленных переменных,
        - количество неявно целочисленных переменных,
        - количество вещественных переменных
        """
        return re.compile(
            r"^(\d+)\s\((\d+)\sbinary,\s(\d+)\sinteger,"
            r"\s(\d+)\simplicit integer,\s(\d+)\scontinuous\)$"
        ).findall(value)

    def _regex_extract_conss_stats(self, value: str) -> list:
        """
        Извлекает количество ограничений
        из переданной строки
        """
        return re.compile(r"^(\d+)\sinitial").findall(value)

    def _regex_delete_sub_string(
        self, value: str, sub_string_for_del: str, *, how_to_replace: str = ""
    ) -> str:
        """
        Удалаяет заданную подстроку из целевой стоки
        """
        sub_string = re.compile(r"(\s+\(.*\))$").findall(value)[0]

        return value.replace(sub_string, how_to_replace)

    def _regex_extract_nodes(self, value: str) -> t.List[t.Tuple]:
        """
        Извлекает число узлов
        """
        return re.compile(r"^(\d+) \((\d+) internal, (\d+) leaves\)").findall(value)

    def _regex_extract_repropagations(self, value: str) -> t.List[t.Tuple]:
        """
        Извлекает число повторных
        распространений по дереву ветвей-и-границ
        """
        return re.compile(r"^(\d+) \((\d+) domain reductions, (\d+) cutoffs\)").findall(
            value
        )

    def _regex_extract_estimation_tree(self, value: str) -> t.List[t.Tuple]:
        """
        Извлекает оценку дерева ветвей-и-границ
        """
        return re.compile(
            r"^(\d+) nodes \((\d+) visited, " r"(\d+) internal, (\d+) leaves, (\d+) open"
        ).findall(value)

    def _regex_extract_sol_sols_found(self, value: str) -> t.List[t.Tuple]:
        """
        Извлекает информацию по найденным решениям
        """
        return re.compile(
            r"^([+-]?\d[.]\d+e\+\d+)\s+.*\(in run (\d+), after (\d+) nodes, "
            r"(\d+[.]\d+) seconds, depth (\d+), found by <(\w+)>\)"
        ).findall(value)

    def _regex_extract_gap(self, value: str) -> t.List[t.Tuple]:
        """
        Извлекает велечину найденного зазора
        """
        return re.compile(r"^(\d+[.]\d+)\s\%").findall(value)

    def get_param(self, param_name: str) -> t.Any:
        """
        Возвращает значение по ключу
        """
        return self._structure_of_doc.get(param_name, "-")

    def _append_value(self, key, value) -> t.NoReturn:
        """
        Добавляет символ "-" к строке
        и создает пару в словаре структуры stat-файла
        """
        values: t.List = value.split()
        values.append("-")
        self._structure_of_doc[key] = (ServiceAttributes._ONE_BLANK).join(values)

    def _extend_value(self, key, value, times: int = 3) -> t.NoReturn:
        """
        Добавляет несколько символов "-" к строке
        и создает пару в словаре структуры stat-файла
        """
        values: t.List = value.split()
        values.extend(["-"] * times)
        self._structure_of_doc[key] = value

    def _append_insert_value(self, key, value, pos: int = 2) -> t.NoReturn:
        """
        Добавляет символ "-" в конец строки и
        вставляет символ "-" в заданную позицию
        """
        values: t.List = value.split()
        values.append("-")
        values.insert(pos, "-")
        self._structure_of_doc[key] = (ServiceAttributes._ONE_BLANK).join(values)


def heatmap_comparison_plot(
    *,
    stat_file_left: StatFileParser,
    stat_file_right: StatFileParser,
    section_name: str,
    suptitle: str,
    title_left_plot: str,
    title_right_plot: str,
    title_diff: str,
    plot_params: t.Optional[dict] = None,
    cmap: t.Optional[
        t.Union[
            str,
            seaborn.palettes._ColorPalette,
            matplotlib.colors.LinearSegmentedColormap,
        ]
    ] = None,
    cmap_diff: t.Optional[
        t.Union[
            str,
            seaborn.palettes._ColorPalette,
            matplotlib.colors.LinearSegmentedColormap,
        ]
    ] = None,
    vmins_vmaxs: t.Optional[t.List[t.Tuple]] = None,
    figsize: t.Tuple[int, int] = (30, 18),
    save_fig: bool = False,
    path_to_save_fig: t.Optional[t.Union[str, pathlib2.Path]] = None,
    dpi: int = 350,
) -> t.NoReturn:
    """
    Отрисовывает тепловые карты двух сравниваемых кадров данных и
    их поэлементую разность
    """
    _N_ROWS, _N_COLS = 1, 3
    fig, (ax_left, ax_right, ax_diff) = plt.subplots(
        nrows=_N_ROWS, ncols=_N_COLS, figsize=figsize
    )

    stat_df_left = stat_file_left.get_section(section_name).sort_index()
    stat_df_right = stat_file_right.get_section(section_name).sort_index()

    dfs = (stat_df_left, stat_df_right, stat_df_left - stat_df_right)
    fmts = (".2g", ".2g", ".0f")
    cmaps = (cmap, cmap, cmap_diff)
    axes = (ax_left, ax_right, ax_diff)

    plot_params = {} if (plot_params is None) else plot_params

    if vmins_vmaxs is None:
        vmins_vmaxs = [(None, None)] * _N_COLS

    for df, fmt, (vmin, vmax), cmap, ax in zip(dfs, fmts, vmins_vmaxs, cmaps, axes):
        sns.heatmap(
            data=df,
            ax=ax,
            cmap=cmap,
            fmt=fmt,
            vmin=vmin,
            vmax=vmax,
            **plot_params,
        )

    fig.suptitle(suptitle)
    ax_left.set_title(title_left_plot)
    ax_right.set_title(title_right_plot)
    ax_diff.set_title(title_diff)

    plt.tight_layout()

    if save_fig:
        plt.savefig(path_to_save_fig, dpi=dpi)


def vertical_cross_section_table_plot(
    *,
    stat_files: t.List[StatFileParser],
    col_name_for_cross: str,  # имя параметра в stat-файле, по которому будет выполняться срез
    section_name: str,  # имя секции в stat-файле
    labels: t.List[str],
    styles: t.List[str],
    colors: t.List[str],
    ax=None,
    figsize: t.Tuple[int, int] = (15, 6),
    save_fig: bool = False,
    path_to_save_fig: t.Optional[t.Union[str, pathlib2.Path]] = None,
    dpi: int = 350,
) -> t.NoReturn:
    """
    Отрисовывает вертикальный срез по кадру данных
    для нескольких stat-файлов
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)

    stat_dfs: t.List[pd.DataFrame] = []
    for idx, stat_file in enumerate(stat_files):
        stat_df = stat_file.get_section(section_name).loc[:, [col_name_for_cross]]
        stat_df = stat_df.rename(columns={col_name_for_cross: labels[idx]})
        stat_dfs.append(stat_df)

    stat_dfs: pd.DataFrame = pd.concat(stat_dfs, axis=1).dropna().sort_index()

    stat_dfs.plot(
        ax=ax,
        style=styles,
        color=colors,
    )

    ax.set_xticks(
        range(len(stat_dfs.index.to_list())),
        stat_dfs.index.to_list(),
        rotation=90,
    )

    ax.set_ylabel(col_name_for_cross)
    ax.legend()

    plt.tight_layout()

    if save_fig:
        plt.savefig(path_to_save_fig, dpi=dpi)


def vertical_cross_section_table_for_all_params_plot(
    *,
    stat_files: t.List[StatFileParser],
    section_name: str,
    labels: t.List[str],
    styles: t.List[str],
    colors: t.List[str],
    figsize: t.Tuple[int, int] = (15, 5),
) -> t.NoReturn:
    """
    Отрисовывает вертикальный срез по кадру данных
    для всех столбцов секции
    """
    param_names = stat_files[0].get_section(section_name).columns.to_list()

    fig, axes = plt.subplots(nrows=len(param_names), ncols=1, figsize=figsize)

    for idx, param_name in enumerate(param_names):
        vertical_cross_section_table_plot(
            stat_files=stat_files,
            col_name_for_cross=param_name,
            section_name=section_name,
            labels=labels,
            styles=styles,
            colors=colors,
            ax=axes[idx],
        )
