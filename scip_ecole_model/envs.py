import typing as t

import ecole


class SimpleBranchingEnv:
    """
    Класс для создания простого рабочего окружения
    """

    def __init__(
        self,
        observation_function=ecole.observation.NodeBipartite(),
        reward_function=ecole.reward.NNodes(),
        information_function: t.Optional[dict] = None,
        scip_params: t.Optional[dict] = None,
    ):
        self.scip_params = {} if (scip_params is None) else scip_params
        self.observation_function = observation_function
        self.reward_function = reward_function
        self.information_function = (
            {} if (information_function is None) else information_function
        )

    def create_env(self) -> ecole.environment.Branching:
        """
        Создает окружение для агента поиска MILP-решения
        """
        env = ecole.environment.Branching(
            scip_params=self.scip_params,
            observation_function=self.observation_function,
            reward_function=self.reward_function,
            information_function=self.information_function,
        )

        return env
