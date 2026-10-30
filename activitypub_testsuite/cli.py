import os

import click

from .fixtures import install_as_link
from .report.generator import main as report_main


@click.group
def aptest():
    """ActivityPub Test Suite Utilities"""


@aptest.command(context_settings={"show_default": True})
@click.argument(
    "destination",
    metavar="DIRECTORY",
    required=False,
    default="tests",
)
@click.option(
    "--force",
    is_flag=True,
    help="Replace existing files with links",
)
def link(destination: str, force: bool):
    """Link the test modules into DIRECTORY (default: ./tests).

    The test modules ship inside the activitypub_testsuite package, which is
    usually outside the project under test. Some tools (notably the VS Code
    pytest extension) only run tests whose paths are inside the workspace, so
    this creates symlinks to the modules in the current project.
    """
    destination = os.path.abspath(destination)
    try:
        results = install_as_link(destination, force=force)
    except OSError as ex:
        raise click.ClickException(str(ex))

    if not results:
        raise click.ClickException(
            "No test modules found in the activitypub_testsuite package."
        )

    linked = 0
    for action, path in results:
        if action == "exists":
            click.echo(f"Skipping existing file: {path}", err=True)
        else:
            click.echo(f"Linked {path}")
            linked += 1
    click.echo(f"{linked} link(s) created in {destination}")


@aptest.command(context_settings={"show_default": True})
@click.option(
    "--input",
    metavar="FILENAME",
    default="test-report.json",
    help="JSON test data",
)
@click.option(
    "--output",
    metavar="FILENAME",
    default=None,
    help="HTML output file (or stdout)",
)
@click.option(
    "--browser",
    is_flag=True,
    help="Launch browser for HTML report",
)
def report(input: str, output: str, browser: bool):
    """Generate an HTML report from the JSON data produced by pytest."""
    try:
        report_main(input, output, browser=browser)
    except FileNotFoundError as ex:
        raise click.ClickException(ex)
