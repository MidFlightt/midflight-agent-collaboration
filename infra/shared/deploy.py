"""Preview a separate AWS stack; --execute applies the reviewed change set."""

import argparse
import hashlib
import json
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

EXPECTED_ACCOUNT = "825125930394"
STACK = "midflight-shared-communication"
ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="midflight-dev")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument(
        "--config",
        type=Path,
        help="Operator roster for the token RPC pilot. Needed to create the stack or change "
        "the roster; omitted on an update, the roster already deployed is kept.",
    )
    parser.add_argument(
        "--invite-secrets",
        type=Path,
        help="Private signing_key/admin_hash JSON; preserved on later updates",
    )
    parser.add_argument(
        "--github-oauth",
        type=Path,
        help="Private client_id/client_secret JSON for the hosted connector's GitHub sign-in; "
        "preserved on later updates",
    )
    parser.add_argument("--execute", help="Exact change-set ID printed by the preview")
    args = parser.parse_args()
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    if session.client("sts").get_caller_identity()["Account"] != EXPECTED_ACCOUNT:
        raise SystemExit("Wrong AWS account; refusing deployment")
    cf = session.client("cloudformation")
    if args.execute:
        change = cf.describe_change_set(ChangeSetName=args.execute)
        if change["StackName"] != STACK:
            raise SystemExit("Refusing to execute another stack's change set")
        cf.execute_change_set(ChangeSetName=args.execute)
        print(f"Deployment started: {STACK}. Inspect stack events and outputs before sharing URL.")
        return
    # Permission preflight before creating paid resources or uploading artifacts.
    session.client("ec2").describe_vpcs()
    cf.list_stacks(StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE"])
    config_parameter = {"ParameterKey": "ConfigJson", "UsePreviousValue": True}
    if args.config is not None:
        from midflight.communication.cloud import validate_config

        config = json.loads(args.config.read_text())
        validate_config(config)
        config_json = json.dumps(config, separators=(",", ":"))
        if len(config_json.encode()) > 3000:
            raise SystemExit(
                "Roster too large for Lambda environment; use a mounted-config deployment"
            )
        config_parameter = {"ParameterKey": "ConfigJson", "ParameterValue": config_json}
    template = (ROOT / "infra/shared/aws.yaml").read_text()
    cf.validate_template(TemplateBody=template)
    artifact = ROOT / "build/shared/lambda.zip"
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    key = f"shared/{digest}.zip"
    bucket = f"midflight-shared-artifacts-{EXPECTED_ACCOUNT}-{args.region}"
    s3 = session.client("s3")
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as error:
        if error.response["Error"]["Code"] not in {"404", "NoSuchBucket"}:
            raise
        options = (
            {}
            if args.region == "us-east-1"
            else {"CreateBucketConfiguration": {"LocationConstraint": args.region}}
        )
        s3.create_bucket(Bucket=bucket, **options)
        s3.put_public_access_block(
            Bucket=bucket,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
        )
        s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
        s3.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration={
                "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
            },
        )
    s3.upload_file(str(artifact), bucket, key)
    try:
        existing = cf.describe_stacks(StackName=STACK)["Stacks"][0]
        existing_values = {
            p["ParameterKey"]: p.get("ParameterValue", "") for p in existing.get("Parameters", [])
        }
        existing_parameters = set(existing_values)
        outputs = {o["OutputKey"]: o["OutputValue"] for o in existing.get("Outputs", [])}
        status = existing["StackStatus"]
        change_type = "CREATE" if status == "REVIEW_IN_PROGRESS" else "UPDATE"
    except ClientError as error:
        if "does not exist" not in error.response["Error"].get("Message", ""):
            raise
        change_type = "CREATE"
        existing_values, existing_parameters, outputs = {}, set(), {}
    if "UsePreviousValue" in config_parameter:
        if change_type == "CREATE" or "ConfigJson" not in existing_parameters:
            raise SystemExit("Creating the stack needs --config with the operator roster")
        print("Keeping the token RPC roster already deployed (no --config given).")
    # The connector must know its own URL for sign-in, but a Function URL exists only after
    # the first deployment creates it. That deployment serves an "unconfigured" page; the
    # next one passes the URL in. Rerun this script once after the first apply.
    hosted_url = outputs.get("HostedUrl", "").rstrip("/")
    if not hosted_url:
        print("Hosted connector URL not known yet: apply this, then run deploy.py again.")
    hosted_parameters = [{"ParameterKey": "HostedPublicUrl", "ParameterValue": hosted_url}]
    if args.github_oauth:
        oauth = json.loads(args.github_oauth.read_text())
        if not oauth.get("client_id") or not oauth.get("client_secret"):
            raise SystemExit("GitHub OAuth JSON needs client_id and client_secret")
        hosted_parameters += [
            {"ParameterKey": "GitHubClientId", "ParameterValue": oauth["client_id"]},
            {"ParameterKey": "GitHubClientSecret", "ParameterValue": oauth["client_secret"]},
        ]
    elif change_type == "UPDATE":
        hosted_parameters += [
            {"ParameterKey": key, "UsePreviousValue": True}
            for key in ("GitHubClientId", "GitHubClientSecret")
            if key in existing_parameters
        ]
    if hosted_url and not args.github_oauth and not existing_values.get("GitHubClientId"):
        print(
            "No GitHub sign-in configured: the connector will answer 'not configured' "
            "until you rerun with --github-oauth."
        )
    invite_parameters = []
    if args.invite_secrets:
        secrets = json.loads(args.invite_secrets.read_text())
        if len(secrets["signing_key"]) < 32 or len(secrets["admin_hash"]) != 64:
            raise SystemExit("Invalid invite deployment secrets")
        invite_parameters = [
            {"ParameterKey": "InviteSigningKey", "ParameterValue": secrets["signing_key"]},
            {"ParameterKey": "InviteAdminHash", "ParameterValue": secrets["admin_hash"]},
        ]
    elif change_type == "UPDATE":
        invite_parameters = [
            {"ParameterKey": key, "UsePreviousValue": True}
            for key in ("InviteSigningKey", "InviteAdminHash")
            if key in existing_parameters
        ]
    result = cf.create_change_set(
        StackName=STACK,
        ChangeSetName=f"shared-{int(time.time())}",
        ChangeSetType=change_type,
        TemplateBody=template,
        Capabilities=["CAPABILITY_IAM"],
        Parameters=[
            {"ParameterKey": k, "ParameterValue": v}
            for k, v in {"ArtifactBucket": bucket, "ArtifactKey": key}.items()
        ]
        + [config_parameter]
        + invite_parameters
        + hosted_parameters,
    )
    cf.get_waiter("change_set_create_complete").wait(ChangeSetName=result["Id"])
    changes = cf.describe_change_set(ChangeSetName=result["Id"])
    for item in changes.get("Changes", []):
        resource = item["ResourceChange"]
        print(
            resource["Action"],
            resource["LogicalResourceId"],
            resource["ResourceType"],
            "replacement=" + resource.get("Replacement", "n/a"),
        )
    print("Change set:", result["Id"])
    print("Review database/volume replacements before executing. No stack resources applied yet.")


if __name__ == "__main__":
    main()
