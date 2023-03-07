import json
import os
import re

CORRECT_UNICODE = "\u2713"
WRONG_UNICODE = "\u2715"
CONNECTOR_CATEGORY = ['Analytics and SIEM', 'Authentication', 'Case Management', 'Threat Intelligence', 'Database',
                      'Deception', 'Email Gateway', 'Endpoint Security', 'Identity and Access Management',
                      'Authentication', 'Insider Threat', 'IT Services', 'Network Security', 'Utilities',
                      'Vulnerability and Risk Management', 'OT & IoT Security', 'Communication and Coordination',
                      'Compliance and Reporting', 'FortiSOAR Essentials', 'Monitoring',
                      'Firewall and Network Protection', 'Threat Hunting and Search', 'Web Application',
                      'Task Management', 'Enterprise mobility management', 'Digital assistant', 'Automation controller',
                      'Logging', 'Query Service', 'Threat Detection', 'Breach and Attack Simulation (BAS)',
                      'ML Service', 'Message Queueing Service', 'Security Posture Management', 'Compute Platform',
                      'Storage', 'Asset Management', 'Container Services', 'IT Service Management',
                      'Attack surface management', 'Malware Analysis', 'Cloud access security broker (CASB)',
                      'Cloud Security', 'Email Server', 'Email Security',
                      'DevOps and Digital Operations and Digital Operations', 'Ticket Management', 'Other']
OPERATION_CATEGORY = ["investigation", "containment", "remediation", "miscellaneous"]
PARAMETER_CATEGORY = ["text", "textarea", "integer", "datetime", "select", "multiselect", "checkbox", "password",
                      "json", "apiOperation"]


def get_info_file_path():
    info_file_path = None
    for dirname, dirnames, filenames in os.walk('.'):
        if dirname in [".git", ".github"]:
            continue
        if "info.json" in filenames:
            info_file_path = dirname + "/info.json"
            break
    return info_file_path, dirname


def read_info(info_file_path: str) -> dict:
    file = open(info_file_path, "r")
    info = json.load(file)
    file.close()
    return info


class TestConnectorInfoSanity:
    def __init__(self, *args, **kwargs):
        self.info_file_path, self.dirname = get_info_file_path()
        self.connector_info = read_info(self.info_file_path)
        self.report = ""
        self.error = ""
        self.failed_test_count = 0
        self.passed_test_count = 0
        if self.connector_info:
            self.init_test()
        else:
            self.report += "Info.json not found.\n"

    def append_correct(self, message: str):
        self.passed_test_count += 1
        self.report += f"\033[32m{CORRECT_UNICODE} {message}\033[0m\n"

    def append_wrong(self, message: str):
        self.failed_test_count += 1
        self.report += f"\033[31m{WRONG_UNICODE} {message}\033[0m\n"
        self.error += f"\033[31m{WRONG_UNICODE} {message}\033[0m\n"

    def init_test(self):
        self.verify_connector_name()
        self.verify_connector_version()
        self.verify_connector_publisher()
        self.verify_connector_category()
        self.verify_connector_logo()
        self.verify_connector_docs_link()
        self.verify_configurations()

        for op in self.connector_info.get("operations", []):
            self.verify_operation(op)

    def verify_connector_name(self):
        folder_name = self.dirname.split("/")[-1]
        if self.connector_info.get("name") == folder_name:
            self.append_correct("Connector name is valid.")
        else:
            self.append_wrong("Connector name is invalid.")

    def verify_connector_label(self):
        conn_label = self.connector_info.get("label")
        if conn_label:
            self.append_correct("Connector label is available.")
        else:
            self.append_wrong("Connector label is missing.")

    def verify_connector_version(self):
        conn_version = self.connector_info.get("version")
        valid_version_regex_pattern = re.compile("^[1-9]\\d*\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$")
        if conn_version and re.fullmatch(valid_version_regex_pattern, conn_version):
            self.append_correct("Connector version is available and valid.")
        elif conn_version:
            self.append_wrong(f"Connector version is available, but invalid. Connector version: '{conn_version}'")
        else:
            self.append_wrong("Connector version is missing.")

    def verify_connector_publisher(self):
        conn_certified = self.connector_info.get("cs_approved")
        conn_publisher = self.connector_info.get("publisher", "")
        if conn_publisher:
            self.append_correct("Connector publisher is available.")
        else:
            self.append_wrong("Connector publisher is missing.")

        if conn_certified and conn_publisher.strip() != "Fortinet":
            self.append_wrong(f"Connector is certified, publisher is should be 'Fortinet'."
                              f"But connector publisher is: '{conn_publisher}'")
        if not conn_certified and conn_publisher.strip() != "Community":
            self.append_wrong(f"Connector is not certified, publisher name should be 'Community'.But connector "
                              f"publisher is: '{conn_publisher}'")

    def verify_connector_descriptions(self):
        conn_desc = self.connector_info.get("description")
        if conn_desc:
            self.append_correct(f"Connector description is available.")
        else:
            self.append_wrong(f"Connector description is missing.")

        if len(conn_desc) < len(self.connector_info.get("label")) * 3:
            self.append_wrong("Connector description is too short.")

    def verify_connector_category(self):
        category = self.connector_info.get("category")
        if category is not None and category in CONNECTOR_CATEGORY:
            self.append_correct("Connector category is valid.")
        else:
            self.append_wrong(f"Connector category is invalid. Category value: '{category}'")

    def verify_connector_logo(self):
        small_logo = self.connector_info.get("icon_small_name")
        large_logo = self.connector_info.get("icon_large_name")
        if small_logo and large_logo:
            self.append_correct("Connector logo is available.")
        else:
            self.append_wrong(
                f"Connector logo is invalid. Small logo value: '{small_logo}'; Large logo value: '{large_logo}'")

    def verify_connector_docs_link(self):
        doc_link = self.connector_info.get("help_online", "").strip()

        if doc_link and doc_link.startswith("https://docs.fortinet.com/document/fortisoar"):
            self.append_correct("Connector doc link is available and valid.")
        elif doc_link:
            self.append_wrong(f"Connector doc link is available, but it is invalid. Connector Doc Link: '{doc_link}'")
        else:
            self.append_wrong(f"Connector doc link is missing.")

    def verify_configurations(self):
        fields = self.connector_info.get("configuration", {}).get("fields")
        for field in fields:
            self.verify_parameter("Configurations", field)

    def verify_operation(self, operation):
        self.verify_operation_name(operation)
        self.verify_operation_title(operation)
        self.verify_operation_category(operation)

        for param in operation.get("parameters"):
            self.verify_parameter(operation.get("title"), param)

    def verify_operation_name(self, operation):
        op_name = operation.get("operation")
        if op_name:
            self.append_correct(f"Operation '{op_name}' is available.")
        else:
            self.append_wrong(f"Operation name is missing.")

    def verify_operation_title(self, operation):
        op_title = operation.get("title")
        if op_title:
            self.append_correct(f"Operation: '{operation.get('operation')}'; Operation title is available.")
        else:
            self.append_wrong(f"Operation: '{operation.get('operation')}'; Operation title is missing.")

    def verify_operation_category(self, operation):
        op_category = operation.get("category")

        if op_category and op_category in OPERATION_CATEGORY:
            self.append_correct(f"Operation: '{operation.get('operation')}'-> Operation category is valid.")
        elif op_category:
            self.append_wrong(f"Operation: '{operation.get('operation')}'-> Operation category is available but invalid."
                              f"Operation Category: '{op_category}'")
        else:
            self.append_wrong(f"Operation: '{operation.get('operation')}' -> Operation category is missing.")

    def verify_operation_descriptions(self, operation):
        op_desc = operation.get("description")
        if op_desc:
            self.append_correct(f"Operation: '{operation.get('operation')}' -> Operation description is available.")
        else:
            self.append_wrong(f"Operation: '{operation.get('operation')}' -> Operation description is missing.")

        if len(op_desc) < len(operation) * 3:
            self.append_wrong(f"Operation: '{operation.get('operation')}' -> Operation description is too short.")

    def verify_operation_output_schema(self, operation):
        op_output_schema = operation.get("output_schema")
        if op_output_schema:
            self.append_correct(
                f"Operation: '{operation.get('operation')}' -> Operation output schema is available.")
        else:
            self.append_wrong(
                f"Operation: '{operation.get('operation')}' -> Operation output schema is missing.")

    def verify_parameter(self, op_name, params):
        self.verify_parameter_name(op_name, params)
        self.verify_parameter_title(op_name, params)
        self.verify_parameter_type(op_name, params)
        self.verify_parameter_descriptions(op_name, params)

    def verify_parameter_name(self, op_name, params):
        p_name = params.get("name")
        if p_name:
            self.append_correct(f"Operation: '{op_name}' -> Params: '{p_name}' is available.")
        else:
            self.append_wrong(f"Operation: '{op_name}' -> Params: '{p_name}' is missing.")

    def verify_parameter_title(self, op_name, params):
        p_title = params.get("title")
        p_name = params.get("name")
        if p_title:
            self.append_correct(f"Operation: '{op_name}' -> Params: '{p_name}' -> Params title is available.")
        else:
            self.append_wrong(f"Operation: '{op_name}' -> Params: '{p_name}' -> Params title is missing.")

    def verify_parameter_type(self, op_name, params):
        p_type = params.get("type")
        p_name = params.get("name")
        if p_type and p_type in PARAMETER_CATEGORY:
            self.append_correct(f"Operation: '{op_name}' -> Params: '{p_name}' -> Params type is available.")
        else:
            self.append_wrong(f"Operation: '{op_name}' -> Params: '{p_name}' -> Params type is missing.")

    def verify_parameter_descriptions(self, op_name, params):
        p_desc = params.get("description")
        p_name = params.get("name")
        if p_desc:
            self.append_correct(f"Operation: '{op_name}' -> Params: '{p_name}' -> Params description is available.")
        else:
            self.append_wrong(f"Operation: '{op_name}' -> Params: '{p_name}' -> Params descriptions is missing.")

        if len(p_desc) < len(p_name) * 3:
            self.append_wrong(f"Operation: '{op_name}' -> Params: '{p_name}' -> Params descriptions is short.")


def main():
    test_conn = TestConnectorInfoSanity()
    print("----------------Report Start--------------")
    print(test_conn.report)
    print("----------------Report End----------------\n\n")

    if test_conn.error:
        error_msg = f"\033[31mAll the checks didn't pass. '{test_conn.failed_test_count}' checks failed out of " \
                    f"'{test_conn.passed_test_count + test_conn.failed_test_count}' checks.\n" + test_conn.error
        raise Exception(error_msg)


if __name__ == '__main__':
    main()
