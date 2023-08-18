# pytest plugins


def pytest_load_initial_conftests(args):
    args.extend(
        [
            "--json-report",
            "--json-report-indent=2",
            "--json-report-omit",
            "collectors",
            "keywords",
        ]
    )
