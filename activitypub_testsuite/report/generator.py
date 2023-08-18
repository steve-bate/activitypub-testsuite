import json
import os
import webbrowser

import jinja2

from activitypub_testsuite.report.filters import configure_filters


def main(json_report_filename, *, browser=False):
    base_dir = os.path.dirname(os.path.realpath(__file__))
    templates = jinja2.Environment(
        loader=jinja2.FileSystemLoader(os.path.join(base_dir, "templates"))
    )
    configure_filters(templates)
    with open(json_report_filename) as fp:
        json_report = json.load(fp)
        template = templates.get_template("report.jinja")
        content = template.render(
            data=json_report,
            duration_format="%0.3f",
        )
        if browser:
            with open("/tmp/test_report.html", "w") as fp:
                fp.write(content)
            webbrowser.open("file:///tmp/test_report.html", new=0)
        else:
            print(content)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", action="store_true")
    parser.add_argument("report_data_file")
    args = parser.parse_args()
    main(args.report_data_file, browser=args.browser)
