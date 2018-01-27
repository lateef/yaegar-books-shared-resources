import sys
from troposphere import GetAtt, Join, Output, Parameter, Ref, Template
from troposphere.cognito import UserPool, SchemaAttribute, Policies, PasswordPolicy, AdminCreateUserConfig, \
    UserPoolClient, IdentityPool, CognitoIdentityProvider, IdentityPoolRoleAttachment
from troposphere.iam import Role, Policy

env = sys.argv[1]

COMPONENT_NAME = "YaegarBooksCognito"

t = Template(COMPONENT_NAME)

t.add_version("2010-09-09")

t.add_description(COMPONENT_NAME + " stacks for env " + env)

userPoolUsers = t.add_resource(
    UserPool(
        "UserPool" + COMPONENT_NAME + "Users",
        UserPoolName="UserPool" + COMPONENT_NAME + "Users",
        AliasAttributes=["email"],
        Schema=[SchemaAttribute(
            Name="email",
            AttributeDataType="String",
            Required="True",
            Mutable="True"
        ),
            SchemaAttribute(
                Name="setup_state",
                AttributeDataType="String",
                Required="False",
                Mutable="True"
            )],
        Policies=Policies(
            PasswordPolicy=PasswordPolicy(
                MinimumLength=6,
                RequireLowercase="True",
                RequireUppercase="True",
                RequireNumbers="True"
            )
        ),
        AdminCreateUserConfig=AdminCreateUserConfig(
            AllowAdminCreateUserOnly="False",
            UnusedAccountValidityDays=7
        ),
        AutoVerifiedAttributes=["email"],
        EmailVerificationMessage='''Welcome to YaegarBooks,
Thanks for registering for a YaegarBooks account, please click the link to verify your email address. {####}

Welcome
YaegarBooks''',
        EmailVerificationSubject="Your verification link"
    )
)

userPoolClientUsers = t.add_resource(
    UserPoolClient(
        "UserPoolClient" + COMPONENT_NAME + "Users",
        ClientName="UserPoolClient" + COMPONENT_NAME + "Users",
        UserPoolId=Ref(userPoolUsers),
        GenerateSecret="False"
    )
)

identityPoolUsers = t.add_resource(
    IdentityPool(
        "IdentityPool" + COMPONENT_NAME + "Users",
        IdentityPoolName="IdentityPool" + COMPONENT_NAME + "Users",
        AllowUnauthenticatedIdentities=False,
        CognitoIdentityProviders=[
            CognitoIdentityProvider(
                ClientId=Ref(userPoolClientUsers),
                ProviderName=GetAtt(userPoolUsers, "ProviderName")
            )
        ]
    )
)

cognitoUnAuthorizedRole = t.add_resource(
    Role(
        "CognitoUnAuthorizedRole",
        RoleName="Cognito_YaegarBooksUnauth_Role",
        AssumeRolePolicyDocument={
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": ["cognito-identity.amazonaws.com"]
                },
                "Action": ["sts:AssumeRoleWithWebIdentity"],
                "Condition": {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": Ref(identityPoolUsers)
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "unauthenticated"
                    }
                }
            }]
        },
        Policies=[
            Policy(
                PolicyName="cognitounauth",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "mobileanalytics:PutEvents",
                            "cognito-sync:*"
                        ],
                        "Resource": ["*"]
                    }]
                }
            )]
    )
)

cognitoAuthorizedRole = t.add_resource(
    Role(
        "CognitoAuthorizedRole",
        RoleName="Cognito_YaegarBooksAuth_Role",
        AssumeRolePolicyDocument={
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {
                    "Federated": ["cognito-identity.amazonaws.com"]
                },
                "Action": ["sts:AssumeRoleWithWebIdentity"],
                "Condition": {
                    "StringEquals": {
                        "cognito-identity.amazonaws.com:aud": Ref(identityPoolUsers)
                    },
                    "ForAnyValue:StringLike": {
                        "cognito-identity.amazonaws.com:amr": "authenticated"
                    }
                }
            }]
        },
        Policies=[
            Policy(
                PolicyName="cognitoauth",
                PolicyDocument={
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": [
                            "mobileanalytics:PutEvents",
                            "cognito-sync:*",
                            "cognito-identity:*"
                        ],
                        "Resource": ["*"]
                    }]
                }
            )]
    )
)

identityPoolRoleAttachment = t.add_resource(
    IdentityPoolRoleAttachment(
        "IdentityPoolRoleAttachment",
        IdentityPoolId=Ref(identityPoolUsers),
        Roles={
            "authenticated": GetAtt(cognitoAuthorizedRole, "Arn"),
            "unauthenticated": GetAtt(cognitoUnAuthorizedRole, "Arn")
        }
    )

)
t.add_output([
    Output(
        "UserPoolArn",
        Value=GetAtt(userPoolUsers, "Arn"),
        Description="UserPool arn for YaegarBooks"
    ),
    Output(
        "UserPoolClientId",
        Value=Ref(userPoolClientUsers),
        Description="UserPoolClient id for YaegarBooks"
    ),
    Output(
        "IdentityPoolId",
        Value=Ref(identityPoolUsers),
        Description="IdentityPool id for YaegarBooks"
    )
])

print(t.to_json())
