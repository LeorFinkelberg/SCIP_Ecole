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
