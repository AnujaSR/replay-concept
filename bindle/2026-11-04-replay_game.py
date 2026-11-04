import marimo

__generated_with = "0.23.2"
app = marimo.App(width="medium", auto_download=["html"])


@app.cell
def _():
    import pandas as pd
    import seaborn as sns
    import random as random
    import matplotlib.pyplot as plt

    return pd, sns


@app.cell
def _(pd, sns):
    df = pd.read_csv(
        "https://raw.githubusercontent.com/FergusonAJ/gp-replays/refs/heads/main/experiments/2026_05_13_01__small_large_double_mut/hpc/data/combined_replay_data.csv"
    )

    # Make relevant_data dataframe to plot prob of finding soln vs replay_gen. This is data provided to orchestrator.
    df["replay_gen"] = df["replay_gen"].str.extract(r"(\d+)").astype(int)
    relevant_data = pd.DataFrame(
        {
            "replay_gen": df["replay_gen"],
            "found_solution": df["found_solution"],
        }
    )
    relevant_data = relevant_data.groupby("replay_gen").mean()

    sns.lineplot(relevant_data)
    return


@app.cell
def _(pd):
    # Players that use different strats to find del_prob_max. Inputs: gen_available = [first, last] gens you can replay from; prev_replays = df(columns = ['replay_gen', 'prob_success']). Outputs: [Is this a guess for del_prob_max, gen to run replay from] = [True/False, gen]

    # Asks for all generations one by one then calculates differences and finds greatest difference
    def brute_force_player(
        gen_available: list, prev_replays: pd.DataFrame
    ) -> list:
        gen_list = list(range(gen_available[0], gen_available[1] + 1))
        del_prob_max = [False, gen_available[0]]

        if len(prev_replays) == len(
            gen_list
        ):  # After guessing all gens to get data, find del_prob_max
            del_prob_max[0] = True
            diff = 0
            prev_prob = -1
            for index, row in prev_replays.iterrows():
                gen = row["replay_gen"]
                prob = row["prob_success"]

                if prev_prob > -1:
                    if prob - prev_prob > diff:
                        diff = prob - prev_prob
                        del_prob_max[1] = int(gen)
                prev_prob = prob
        else:  # Ask for prob for next gen
            del_prob_max[1] = gen_list[len(prev_replays)]

        return del_prob_max

    return (brute_force_player,)


@app.cell
def _(brute_force_player, pd):
    def test_brute_force_player_first_guess():
        prev_replays = pd.DataFrame({"replay_gen": [], "prob_success": []})
        assert brute_force_player([1, 5], prev_replays) == [False, 1]

    def test_brute_force_player_asks_for_next():
        prev_replays = pd.DataFrame(
            {"replay_gen": [1, 2, 3], "prob_success": [0.2, 0.25, 0.8]}
        )
        assert brute_force_player([1, 5], prev_replays) == [False, 4]

    def test_brute_force_player_guesses_del_p():
        prev_replays = pd.DataFrame(
            {
                "replay_gen": [1, 2, 3, 4, 5],
                "prob_success": [0.2, 0.25, 0.8, 0.85, 1],
            }
        )
        assert brute_force_player([1, 5], prev_replays) == [True, 3]

    def test_brute_force_player_one_gen():
        prev_replays = pd.DataFrame({"replay_gen": [1], "prob_success": [0.2]})
        assert brute_force_player([1, 1], prev_replays) == [True, 1]

    return


@app.cell
def _(pd):
    # Orchestrators: They are provided the data and the player, and return prev_replays to the player until the player guesses del_prob_max.

    # This is the simple version in which the player guesses the gen and the orchestrator replays 100 times and returns the probability of that gen being successful.

    def replay_100_return_prob(
        dataset: pd.DataFrame, player: list
    ) -> pd.DataFrame:
        prev_replays = pd.DataFrame({"replay_gen": [], "prob_success": []})

        columns = dataset.columns.tolist()
        replay_gen = columns[0]
        prob_found_solution = columns[1]

        request = player(
            [dataset[replay_gen].iloc[0], dataset[replay_gen].iloc[-1]],
            prev_replays,
        )

        while (
            request[0] == False
        ):  # Give it the prob if it's not guessing del_prob_max
            gen = request[1]
            prob_success = dataset.loc[
                dataset[replay_gen] == gen, prob_found_solution
            ].iloc[0]
            prev_replays.loc[len(prev_replays)] = [gen, prob_success]
            request = player(
                [dataset[replay_gen].iloc[0], dataset[replay_gen].iloc[-1]],
                prev_replays,
            )

        gen = request[1]
        prob_success = dataset.loc[
            dataset[replay_gen] == gen, prob_found_solution
        ].iloc[0]
        prev_replays.loc[len(prev_replays)] = [gen, prob_success]
        prev_replays["replay_gen"] = prev_replays["replay_gen"].astype(int)

        return prev_replays

    # This orchestrator only replays once, and returns whether the replay gave a success or fail (0 or 1)

    def replay_100_return_prob(
        dataset: pd.DataFrame, player: list
    ) -> pd.DataFrame:
        prev_replays = pd.DataFrame({"replay_gen": [], "prob_success": []})

        columns = dataset.columns.tolist()
        replay_gen = columns[0]
        prob_found_solution = columns[1]

        request = player(
            [dataset[replay_gen].iloc[0], dataset[replay_gen].iloc[-1]],
            prev_replays,
        )

        while (
            request[0] == False
        ):  # Give it the prob if it's not guessing del_prob_max
            gen = request[1]
            prob_success = dataset.loc[
                dataset[replay_gen] == gen, prob_found_solution
            ].iloc[0]
            prev_replays.loc[len(prev_replays)] = [gen, prob_success]
            request = player(
                [dataset[replay_gen].iloc[0], dataset[replay_gen].iloc[-1]],
                prev_replays,
            )

        gen = request[1]
        prob_success = dataset.loc[
            dataset[replay_gen] == gen, prob_found_solution
        ].iloc[0]
        prev_replays.loc[len(prev_replays)] = [gen, prob_success]
        prev_replays["replay_gen"] = prev_replays["replay_gen"].astype(int)

        return prev_replays

    return (replay_100_return_prob,)


@app.cell
def _(brute_force_player, pd, replay_100_return_prob):
    def test_replay_100_return_prob_first_last_call():
        player = brute_force_player
        data = pd.DataFrame({"replay_gen": [1], "found_solution": [0.2]})
        output = pd.DataFrame(
            {"replay_gen": [1, 1], "prob_success": [0.2, 0.2]}
        )
        pd.testing.assert_frame_equal(
            replay_100_return_prob(data, player), output
        )

    return


@app.cell
def _(player_data):
    def evaluator(player_list, orchestrator):
        return player_data

    return


if __name__ == "__main__":
    app.run()
