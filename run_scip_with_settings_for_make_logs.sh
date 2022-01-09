#!/bin/bash
scip \
    -s settings_for_scip_solver/scip_without_presolving.set \
    -c "read input_for_model/ikp_milp_problem.lp optimize quit" \
    > output_from_model/scip_output_wo_presolving_and_separating.log
