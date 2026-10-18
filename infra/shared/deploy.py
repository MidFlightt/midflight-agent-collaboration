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
    parser.add_argument("--config", type=Path)
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
    if args.config is None:
        parser.error("--config is required for a preview")
    # Permission preflight before creating paid resources or uploading artifacts.
    session.client("ec2").describe_vpcs()
    cf.list_stacks(StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE"])
    from midflight.communication.cloud import validate_config

    config = json.loads(args.config.read_text())
    validate_config(config)
    config_json = json.dumps(config, separators=(",", ":"))
    if len(config_json.encode()) > 3000:
        raise SystemExit("Roster too large for Lambda environment; use a mounted-config deployment")
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
        status = cf.describe_stacks(StackName=STACK)["Stacks"][0]["StackStatus"]
        change_type = "CREATE" if status == "REVIEW_IN_PROGRESS" else "UPDATE"
    except ClientError as error:
        if "does not exist" not in error.response["Error"].get("Message", ""):
            raise
        change_type = "CREATE"
    result = cf.create_change_set(
        StackName=STACK,
        ChangeSetName=f"shared-{int(time.time())}",
        ChangeSetType=change_type,
        TemplateBody=template,
        Capabilities=["CAPABILITY_IAM"],
        Parameters=[
            {"ParameterKey": k, "ParameterValue": v}
            for k, v in {
                "ArtifactBucket": bucket,
                "ArtifactKey": key,
                "ConfigJson": config_json,
            }.items()
        ],
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
