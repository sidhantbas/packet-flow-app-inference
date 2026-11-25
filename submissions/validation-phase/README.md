# Validation Phase files (train-only models)

Each folder holds `submission.json` and `submission.zip` for the Validation Phase: Task 1 from the named model, Task 2 from production (014); every model fitted on the train split only. Scores below come from the unchanged official `evaluate()` run locally against the public validation labels; the platform should show the same numbers. **Pipeline check and single-split view only: the Validation Phase does not count for the ranking, and models are never chosen by these scores (selection = 50-fold CV).**

| folder                   | model                                     |   Task 1 Macro F1 |   Task 1 Accuracy |   Task 1 Score |   Task 2 Macro F1 |   Task 2 Accuracy |   Task 2 Score |   Total |
|:-------------------------|:------------------------------------------|------------------:|------------------:|---------------:|------------------:|------------------:|---------------:|--------:|
| production-034           | production-034                            |            0.8518 |            0.9036 |        42.5914 |            0.7781 |            0.8795 |        38.9073 | 81.4987 |
| 022-whole-flow-blend     | 022-whole-flow-blend (84.62 file's model) |            0.7625 |            0.8916 |        38.1235 |            0.7781 |            0.8795 |        38.9073 | 77.0308 |
| 004-softvote             | 004-softvote (83.56 file's model)         |            0.7447 |            0.8795 |        37.233  |            0.7781 |            0.8795 |        38.9073 | 76.1403 |
| 065-rest-expert          | 065-rest-expert (066 file)                |            0.8842 |            0.9398 |        44.2125 |            0.7781 |            0.8795 |        38.9073 | 83.1198 |
| 077-fingerprint-rest     | 077-fingerprint-rest                      |            0.8643 |            0.9157 |        43.2129 |            0.7781 |            0.8795 |        38.9073 | 82.1202 |
| 062-nonmeta-thresholds   | 062-nonmeta-thresholds                    |            0.8518 |            0.9036 |        42.5914 |            0.7781 |            0.8795 |        38.9073 | 81.4987 |
| 075-rest-plus-thresholds | 075-rest-plus-thresholds                  |            0.8842 |            0.9398 |        44.2125 |            0.7781 |            0.8795 |        38.9073 | 83.1198 |
