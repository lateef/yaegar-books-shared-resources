import sys
from troposphere import GetAtt, Join, Output, Parameter, Ref, Template
from troposphere.s3 import Bucket, Private

env = sys.argv[1]

COMPONENT_NAME = env + "YaegarBooksSharedResources"

t = Template(COMPONENT_NAME)

t.add_version("2010-09-09")

t.add_description(COMPONENT_NAME + " stacks")

s3bucket = t.add_resource(
    Bucket(
        "S3BucketSharedResources",
        AccessControl=Private
    )
)

t.add_output([
    Output(
        "S3bucketArn",
        Value=GetAtt(s3bucket, "Arn"),
        Description="Arn for S3"
    )
])

print(t.to_json())
