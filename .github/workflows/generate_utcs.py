import json
import os

DEFAULT_UTC = "- [ ] Connector installation verified.\n" \
               "- [ ] Connector logo verified.\n" \
               "- [ ] Docs link verified.\n" \
               "- [ ] Actions and Playbooks list verified.\n" \
               "- [ ] Playbooks tags verified.\n" \
               "- [ ] All playbooks are in info mode verified.\n" \
               "- [ ] All playbooks are in inactive mode verified.\n" \
               "- [ ] Ingestion playbooks are verified.\n" \
               "- [ ] Check health verified.\n"


def add_effected_actions(template: str, info: dict) -> str:
    template += "\n#### Affected Actions:\n"
    template += "- [ ] All\n"
    template += "- [ ] Check Health\n"

    actions = info.get("operations", [])
    for action in actions:
        template += f"- [ ] {action.get('title')}\n"
    if not actions:
        template += "_Add changes impact here_\n"
    return template


def add_unit_test_cases(template: str, info: dict) -> str:
    template += "\n#### UTCs:\n"

    template += DEFAULT_UTC

    actions = info.get("operations", [])
    for action in actions:
        template += f"- [ ] {action.get('title')} action verified.\n"
    return template


def read_info(info_file_path: str) -> dict:
    file = open(info_file_path, "r")
    info = json.load(file)
    file.close()
    return info


def get_info_file_path():
    info_file_path = None
    for dirname, dirnames, filenames in os.walk('.'):
        if dirname in [".git", ".github"]:
            continue
        if "info.json" in filenames:
            info_file_path = dirname + "/info.json"
            break
    return info_file_path


def create_template(info: dict) -> str:
    template = "### Please select effected actions and Performed checks.\n\n"
    template = add_effected_actions(template, info)
    template = add_unit_test_cases(template, info)
    return template


def main() -> None:
    info_file_path = get_info_file_path()
    if info_file_path is None:
        raise Exception("info.json not found.")
    info = read_info(info_file_path)
    template = create_template(info)
    print(template)


if __name__ == '__main__':
    main()
