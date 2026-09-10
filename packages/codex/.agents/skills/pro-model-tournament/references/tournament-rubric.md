# Pro model tournament rubric

Create three to five materially different routes per subproblem; use four by default.
Changing only an optimizer, seed, loss weight, or hyperparameter does not create a new
route. Include one interpretable baseline even when it is unlikely to win.

Score each route from 0 to 10 on:

- `task_fit`: correspondence to the mathematical question and deliverables.
- `data_feasibility`: whether available inputs identify and support the model.
- `validation_strength`: ability to falsify, compare, and independently reproduce.
- `robustness`: sensitivity to perturbation, uncertainty, and constraint stress.
- `interpretability`: traceability from assumptions and variables to conclusions.
- `innovation_value`: useful novelty beyond cosmetic complexity.
- `implementation_risk`: 10 means low execution risk; document the raw risks too.

Weights must be declared before scoring and sum to 1.0. Do not tune weights to force a
preferred winner. Every route requires an experiment plan, expected evidence, data
needs, assumptions, failure modes, and estimated computational strategy. The decision
records one selected route, one distinct backup, and a specific rejection reason for
every remaining route. Keep failed experimental candidates in the final manifest.
