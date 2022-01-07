NB: Рекомендуется установить _утилиту управления git-публикациями_ [pre-commit](https://pre-commit.com)
```bash
# Установка
$ pip install pre-commit
$ pre-commit install
$ cat .git/hooks/pre-commit | sed -n "/gener.*/p"
# Порядок работы с утилитой
$ pre-commit --version
$ pre-commit run --color always --all-files
$ pre-commit run <hook_id>
$ pre-commit clean
$ pre-commit gc
```

Запуск решения
```bash
$ python run_scip_ecole_pipeline.py
```

Общая архитектура решения на базе связки SCIP+Ecole

![image_info](./scip_ecole_model/documentation/prospects_ML_algorithms_for_MILP/figures/architec_scip_ecole.PNG)

Реализация с внешним модулем машинного обучения

![image_info](./scip_ecole_model/documentation/prospects_ML_algorithms_for_MILP/figures/architec_scip_ecole_ml.PNG)

Вспомогательные материалы
```bash
# Запуск решателя SCIP в интерактивном режиме
# Прочитать файл математической постановки задачи problem.lp, настроив сессию с помощью scip_params.set
$ scip -s scip_params.set -c "read problem.lp optimize quit"
# Записать логи хода решения SCIP
$ scip -s configs_for_scip_solver/scip_without_presolving.set \
    -c "read input_for_model/ikp_milp_problem.lp optimize quit" > scip.log
```
