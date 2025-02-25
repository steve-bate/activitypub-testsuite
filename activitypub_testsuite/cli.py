import click

from .report.generator import main as report_main


@click.group
def aptest():
    """ActivityPub Test Suite Utilities"""


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
