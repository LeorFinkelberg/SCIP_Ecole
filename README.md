NB: Рекомендуется установить _утилиту управления git-публикациями_ [`pre-commit`](https://pre-commit.com)
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
$ chmod +x run_main_pipeline.sh
-rwxr-xr-x@ 1  staff    45B 10 янв 02:30 run_main_pipeline.sh*
$ ./run_main_pipeline.sh
2022-01-10 02:35:37,909: INFO ->> Procedure for finding solution with `SCIP+Ecole` has been started ...
2022-01-10 02:35:37,914: INFO ->> File `scip_ecole_model_config.yaml` has been read successfully!
2022-01-10 02:35:37,915: INFO ->> File `settings_for_scip_solver/scip_test.set` has been read successfully!
original problem has 743414 variables (0 bin, 168176 int, 0 impl, 575238 cont) and 624143 constraints
...
```

Запуск решателя SCIP с заданными настройками и цепочкой действий
```bash
$ chmod +x run_scip_with_settings_for_make_logs.sh
$ ll run_scip_with_settings_for_make_logs.sh
-rwxr-xr-x  1 leor.finkelberg  staff   216B 10 янв 02:48 run_scip_with_settings_for_make_logs.sh*
$ cat run_scip_with_settings_for_make_logs.sh
#!/bin/bash
scip \
    -s settings_for_scip_solver/scip_without_presolving.set \
    -c "read input_for_model/ikp_milp_problem.lp optimize quit" \
    > output_from_model/scip_output_wo_presolving_and_separating.log
$ ./run_scip_with_settings_for_make_logs.sh
```

Общая архитектура решения на базе связки SCIP+Ecole

![image_info](./scip_ecole_model/documentation/prospects_ML_algorithms_for_MILP/figures/architec_scip_ecole.PNG)

Реализация с внешним модулем машинного обучения

![image_info](./scip_ecole_model/documentation/prospects_ML_algorithms_for_MILP/figures/architec_scip_ecole_ml.PNG)
