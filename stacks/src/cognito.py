import sys
from troposphere import GetAtt, Join, Output, Parameter, Ref, Template
from troposphere.cognito import UserPool, SchemaAttribute, Policies, PasswordPolicy, AdminCreateUserConfig, \
    UserPoolClient, IdentityPool, CognitoIdentityProvider, IdentityPoolRoleAttachment
from troposphere.iam import Role, Policy

env = sys.argv[1]

COMPONENT_NAME = "YaegarBooksUserPool"

t = Template(COMPONENT_NAME)

t.add_version("2010-09-09")

t.add_description(COMPONENT_NAME + " stacks for env " + env)

userPool = t.add_resource(
    UserPool(
        "UserPoolYaegar",
        UserPoolName="yaegaruserpool",
        AliasAttributes=["email"],
        Schema=[SchemaAttribute(
            Name="email",
            AttributeDataType="String",
            Required="True",
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

If you have any questions, please contact our support team at: <email>

                                                                Or call:

<phone number> lines are open Monday to Friday, 9am to 5pm.
    Account details:
Account:
Email:

Welcome
YaegarBooks''',
        EmailVerificationSubject="Your verification link"
    )
)

userPoolClient = t.add_resource(
    UserPoolClient(
        "UserPoolClientYaegarBooks",
        ClientName="yaegarbooksappclient",
        UserPoolId=Ref(userPool),
        GenerateSecret="False"
    )
)

identityPool = t.add_resource(
    IdentityPool(
        "IdentityPoolYaegar",
        IdentityPoolName="YaegarBooksIdentityPool",
        AllowUnauthenticatedIdentities=False,
        CognitoIdentityProviders=[
            CognitoIdentityProvider(
                ClientId=Ref(userPoolClient),
                ProviderName=GetAtt(userPool, "ProviderName")
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
                        "cognito-identity.amazonaws.com:aud":  Ref(identityPool)
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
                        "cognito-identity.amazonaws.com:aud": Ref(identityPool)
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
        IdentityPoolId=Ref(identityPool),
        Roles={
            "authenticated": GetAtt(cognitoAuthorizedRole, "Arn"),
            "unauthenticated": GetAtt(cognitoUnAuthorizedRole, "Arn")
        }
    )

)
t.add_output([
    Output(
        "UserPoolArn",
        Value=GetAtt(userPool, "Arn"),
        Description="UserPool arn for Yaegar"
    ),
    Output(
        "UserPoolClientId",
        Value=Ref(userPoolClient),
        Description="UserPoolClient id for Yaegar"
    ),
    Output(
        "IdentityPoolId",
        Value=Ref(identityPool),
        Description="IdentityPool id for Yaegar"
    )
])

print(t.to_json())
