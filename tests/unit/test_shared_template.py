"""The shared AWS template: every reference resolves, and the hosted connector is wired."""

import importlib
import re
from pathlib import Path

import yaml

TEMPLATE = Path(__file__).resolve().parents[2] / "infra/shared/aws.yaml"


class CloudFormation(yaml.SafeLoader):
    pass


def _tag(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):
        value = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    else:
        value = loader.construct_mapping(node, deep=True)
    return {suffix: value}


CloudFormation.add_multi_constructor("!", _tag)


def load():
    return yaml.load(TEMPLATE.read_text(), Loader=CloudFormation)  # noqa: S506


def test_every_reference_names_a_parameter_or_resource():
    template = load()
    known = set(template["Parameters"]) | set(template["Resources"]) | {"AWS::Region"}
    text = TEMPLATE.read_text()
    refs = set(re.findall(r"!Ref (\w+)", text)) | set(re.findall(r"!GetAtt (\w+)\.", text))
    refs |= {r for r in re.findall(r"\$\{([\w:]+)[}.]", text)}
    for resource in template["Resources"].values():
        depends = resource.get("DependsOn", [])
        refs |= set([depends] if isinstance(depends, str) else depends)
    assert refs - known == set()


def test_hosted_connector_reaches_the_database_and_the_internet():
    resources = load()["Resources"]
    function = resources["HostedFunction"]["Properties"]
    env = function["Environment"]["Variables"]
    module, factory = env["MIDFLIGHT_APP"].split(":")
    assert callable(getattr(importlib.import_module(module), factory))
    assert function["VpcConfig"]["SubnetIds"] == [{"Ref": "PrivateSubnet"}]
    ingress = resources["DatabaseSecurityGroup"]["Properties"]["SecurityGroupIngress"]
    assert {"Ref": "HostedSecurityGroup"} in [rule["SourceSecurityGroupId"] for rule in ingress]
    egress = resources["HostedSecurityGroup"]["Properties"]["SecurityGroupEgress"]
    assert {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "CidrIp": "0.0.0.0/0"} in egress
    assert resources["PrivateRoute"]["Properties"]["NatGatewayId"] == {"Ref": "NatGateway"}
    # The token RPC function is untouched: same app, same subnet.
    original = resources["Function"]["Properties"]
    assert "MIDFLIGHT_APP" not in original["Environment"]["Variables"]
    assert original["VpcConfig"]["SubnetIds"] == [{"Ref": "Subnet"}]


def referenced(node):
    """Resource names a template fragment points at through Ref, GetAtt or Sub."""
    found = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "Ref" and isinstance(value, str):
                found.add(value)
            elif key == "GetAtt" and isinstance(value, str):
                found.add(value.split(".")[0])
            elif key == "Sub" and isinstance(value, str):
                found |= {m.split(".")[0] for m in re.findall(r"\$\{([\w:.]+)\}", value)}
            elif key == "DependsOn":
                found |= set([value] if isinstance(value, str) else value)
            else:
                found |= referenced(value)
    elif isinstance(node, list):
        for item in node:
            found |= referenced(item)
    return found


def test_token_pilot_is_optional_and_nothing_else_depends_on_it():
    template = load()
    pilot = {"Function", "FunctionUrl", "UrlPermission", "InvokePermission", "Logs"}
    resources = template["Resources"]
    assert {n for n, r in resources.items() if r.get("Condition") == "HasRoster"} == pilot
    assert template["Parameters"]["ConfigJson"]["Default"] == ""
    for name, resource in resources.items():
        if name not in pilot:
            assert not referenced(resource) & pilot, name
    for name, output in template["Outputs"].items():
        if referenced(output) & pilot:
            assert output.get("Condition") == "HasRoster", name
