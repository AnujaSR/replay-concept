import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium", auto_download=["html"])


@app.cell
def _():
    import pandas as pd
    import seaborn as sns
    import random as random

    return pd, random, sns


@app.cell
def _(pd, sns):
    df = pd.read_csv(
        "https://raw.githubusercontent.com/FergusonAJ/gp-replays/3044792e334fdd7f1f82bb7f3f410a51b94239e7/experiments/2026_05_13_01__small_large_double_mut/hpc/data/combined_replay_data.csv"
    )

    # Make relevant_data dataframe to plot prob of finding soln vs replay_gen. This is data provided to orchestrator.
    df["replay_gen"] = df["replay_gen"].str.extract(r"(\d+)").astype(int)
    relevant_data = pd.DataFrame(
        {
            "replay_gen": df["replay_gen"],
            "prob_found_solution": df["found_solution"],
        }
    )
    relevant_data = relevant_data.groupby("replay_gen").mean().reset_index()

    sns.lineplot(relevant_data)
    relevant_data
    return (relevant_data,)


@app.cell
def _(pd):
    # Players that use different strats to find del_prob_max. Inputs: gen_available = [first, last] gens you can replay from; prev_replays = df(columns = ['replay_gen', 'outcome']). Outputs: [Is this a guess for del_prob_max, gen to run replay from] = [True/False, gen]

    # Replays from each generation 10 times, then calculates the probabilities to find del_prob_max
    def brute_force_player(
        gen_available: list, prev_replays: pd.DataFrame
    ) -> list:
        gen_list = list(range(gen_available[0], gen_available[1] + 1))
        del_prob_max = [False, gen_available[0]]

        columns = prev_replays.columns.tolist()
        replay_gen = columns[0]
        outcome = columns[1]

        if len(prev_replays) == 10 * len(
            gen_list
        ):  # After guessing all gens 10 times to get data, find del_prob_max
            del_prob_max[0] = True
            diff = 0
            prev_prob = -1
            prev_replays = prev_replays.groupby(
                replay_gen, as_index=False
            ).mean()
            for i in range(len(prev_replays)):
                gen = prev_replays.iloc[i, 0]
                prob = prev_replays.iloc[i, 1]

                if prev_prob > -1:
                    if prob - prev_prob > diff:
                        diff = prob - prev_prob
                        del_prob_max[1] = int(gen)
                prev_prob = prob
        else:  # Ask for prob for next gen
            del_prob_max[1] = gen_list[len(prev_replays) % len(gen_list)]

        return del_prob_max

    return (brute_force_player,)


@app.cell
def _(brute_force_player, pd, random):
    def test_brute_force_player_asks_for_next_gen():
        prev_replays = pd.DataFrame({"replay_gen": [1], "outcome": [1]})
        assert brute_force_player([1, 5], prev_replays) == [False, 2]

    def test_brute_force_player_cycles_middle():
        prev_replays = pd.DataFrame(
            {"replay_gen": [1, 2, 1, 2, 1, 2], "outcome": [1, 1, 0, 0, 0, 1]}
        )
        assert brute_force_player([1, 2], prev_replays) == [False, 1]

    def test_brute_force_player_cycles_end():
        prev_replays = pd.DataFrame(
            {
                "replay_gen": [
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                ],
                "outcome": [
                    1,
                    1,
                    0,
                    0,
                    0,
                    1,
                    1,
                    1,
                    0,
                    0,
                    0,
                    1,
                    1,
                    1,
                    0,
                    0,
                    0,
                    1,
                ],
            }
        )
        assert brute_force_player([1, 2], prev_replays) == [False, 1]

    def test_brute_force_player_finds_del_prob():
        replay_gens = []
        outcomes = []
        for i in range(30):
            if i % 3 != 0:
                replay_gens.append(i % 3)
            else:
                replay_gens.append(3)
            random.seed(i * 99)
            outcomes.append(random.randint(0, 1))

        print(replay_gens)

        prev_replays = pd.DataFrame(
            {"replay_gen": replay_gens, "outcome": outcomes}
        )

        assert brute_force_player([1, 3], prev_replays) == [True, 3]

    return


@app.cell
def _(pd, random):
    # Orchestrators: They are provided the data and the player, and return prev_replays to the player until the player guesses del_prob_max.

    # This orchestrator only replays once, and returns whether the replay gave a success or fail (0 or 1)

    def one_replay_per_call(
        dataset: pd.DataFrame, player: list, seed: int
    ) -> pd.DataFrame:
        prev_replays = pd.DataFrame({"replay_gen": [], "outcome": []})
        # Seed random number here once
        random.seed(seed)

        # Column names
        columns = dataset.columns.tolist()
        replay_gen = columns[0]
        found_solution = columns[1]

        request = player(
            [dataset[replay_gen].iloc[0], dataset[replay_gen].iloc[-1]],
            prev_replays,
        )

        gen = request[1]

        while not request[
            0
        ]:  # Give it the outcome if it's not guessing del_prob_max
            gen = request[1]
            prob_success = dataset.loc[
                dataset[replay_gen] == gen, found_solution
            ].iloc[0]
            if random.random() < prob_success:
                prev_replays.loc[len(prev_replays)] = [gen, 1]
            else:
                prev_replays.loc[len(prev_replays)] = [gen, 0]

            request = player(
                [dataset[replay_gen].iloc[0], dataset[replay_gen].iloc[-1]],
                prev_replays,
            )

        gen = request[1]
        prob_success = dataset.loc[
            dataset[replay_gen] == gen, found_solution
        ].iloc[0]
        if random.random() < prob_success:
            prev_replays.loc[len(prev_replays)] = [gen, 1]
        else:
            prev_replays.loc[len(prev_replays)] = [gen, 0]

        prev_replays["replay_gen"] = prev_replays["replay_gen"].astype(int)

        return prev_replays

    return (one_replay_per_call,)


@app.cell
def _(brute_force_player, one_replay_per_call, pd):
    def test_one_replay_per_call_first_last_call():
        player = brute_force_player
        data = pd.DataFrame({"replay_gen": [1], "prob_found_solution": [1]})
        output = pd.DataFrame(
            {
                "replay_gen": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
                "outcome": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            }
        )
        pd.testing.assert_frame_equal(
            one_replay_per_call(data, player, 1), output
        )

    def test_one_replay_per_call_diff_probs_each_run():
        player = brute_force_player
        data = pd.DataFrame(
            {"replay_gen": [1, 2], "prob_found_solution": [0, 1]}
        )
        output = pd.DataFrame(
            {
                "replay_gen": [
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    1,
                    2,
                    2,
                ],
                "outcome": [
                    0,
                    1,
                    0,
                    1,
                    0,
                    1,
                    0,
                    1,
                    0,
                    1,
                    0,
                    1,
                    0,
                    1,
                    0,
                    1,
                    0,
                    1,
                    0,
                    1,
                    1,
                ],
            }
        )
        pd.testing.assert_frame_equal(
            one_replay_per_call(data, player, 3), output
        )

    return


@app.cell
def _(pd):
    # Evaluation system. Tests whether the guessed del_prob_max is correct, and how many replays each player takes to find del_prob_max.

    def evaluator(
        player_list: list,
        orchestrator: pd.DataFrame,
        dataset: pd.DataFrame,
        numtrials: int,
    ) -> pd.DataFrame:
        player_data = pd.DataFrame(
            {"player": [], "trial": [], "correct_del_p": [], "num_tries": []}
        )
        correct_gen = 39

        for trial in range(numtrials):
            for player in player_list:
                results = orchestrator(dataset, player, trial)
                guessed_gen = results.loc[len(results) - 1, "replay_gen"]
                add = [
                    player.__name__,
                    trial,
                    (correct_gen == guessed_gen).astype(int),
                    len(results) - 1,
                ]
                player_data.loc[len(player_data)] = add

        return player_data

    return (evaluator,)


@app.cell
def _(brute_force_player, evaluator, one_replay_per_call, relevant_data):
    evaluator([brute_force_player], one_replay_per_call, relevant_data, 3)
    return


@app.cell
def _(pd):
    def analyze_data(player_data: pd.DataFrame) -> pd.DataFrame:
        data = pd.DataFrame()
        data = player_data.groupby("player", as_index=False).agg(
            num_trials=("trial", "max"),
            num_successes=("correct_del_p", "sum"),
            avg_num_replays=("num_tries", "mean"),
        )
        # Trials are indexed starting from 0, fixing max error caused by that
        data["num_trials"] = data["num_trials"] + 1

        data["success_rate"] = data["num_successes"] / data["num_trials"]

        return data

    return (analyze_data,)


@app.cell
def _(
    analyze_data,
    brute_force_player,
    evaluator,
    one_replay_per_call,
    relevant_data,
):
    player_data = evaluator(
        [brute_force_player], one_replay_per_call, relevant_data, 20
    )
    analyze_data(player_data)
    return


if __name__ == "__main__":
    app.run()
