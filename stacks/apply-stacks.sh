#!/bin/bash

# Get environment or exit with error message
envs="Int Test Live"
valid_opt=false

usage () {
	echo "Usage: './apply-stack.sh -e <target environment>'";
	echo "Example './apply-stack.sh -e Int'";
	echo "Supported environments are ($envs)";
	exit 1;
 }

while getopts ":e:" opt; do
	case ${opt} in
		e )
			valid_opt=true;

			if [[ ${envs} =~ (^|[[:space:]])$OPTARG($|[[:space:]]) ]]; then
				env=$OPTARG;
			else
				echo "Invalid option argument: -$OPTARG" 1>&2;
				usage;
			fi
		;;
		\? )
			echo "Invalid Option: -$OPTARG" 1>&2
			usage;
		;;
		: )
			echo "Invalid Option: -$OPTARG requires an argument" 1>&2
			usage;
		;;
		 * )
			echo "Unimplemented option" 1>&2
			usage;
		;;
	esac
done
shift $((OPTIND -1))

if [[ ${valid_opt} = false ]]; then
	echo "Missing argument";
	usage;
fi

# Get stack name
stack_name=$(jq ".${env}" stack_names.json | tr -d '"')

stack_status=$(aws cloudformation list-stacks | jq '.StackSummaries[] |
	select(.StackName=="'${stack_name}'" and .StackStatus != "DELETE_COMPLETE") |
 	.StackStatus' | tr -d '"')

if [[ ${stack_status} =~ "FAILED" ]]; then
	echo "Error: ${stack_name} is in ${stack_status} state, exiting...";
	exit 1;
fi

# Build the template
make ENV=${env}

stack_params="--stack-name ${stack_name}"

template_path="--template-body file://build/${stack_name}.json --capabilities CAPABILITY_IAM"

if [[ '' == ${stack_status} ]]; then
	# Create stack
	aws cloudformation create-stack ${stack_params} ${template_path}
	message=$(aws cloudformation wait stack-create-complete ${stack_params} &> /dev/null)
	if [[ "$?" -ne 0 ]]; then
 		echo "Error: Failed to create ${stack_name}";
 		exit 1;
	fi

	echo ${message}
else
	# Update stack
	change_sets=$(aws cloudformation list-change-sets ${stack_params})
	number_of_change_sets=$(echo ${change_sets} | jq '.Summaries|length')

	if [[ ${number_of_change_sets} -gt 0 ]]; then
		echo "Error: ${stack_name} has ${number_of_change_sets} change sets outstanding, please run or delete them";
		exit 1;
	fi

	change_set_name=${stack_name}-$(date -u "+%Y-%m-%dT%H-%M-%SZ");
	change_set_params="--change-set-name ${change_set_name}";

	create_change_set_response=$(aws cloudformation create-change-set ${stack_params} ${template_path} ${change_set_params});
    change_set_arn="$(echo ${create_change_set_response} | jq '.Id' | tr -d '"')";
    echo "Creating change set ${change_set_name} for stack ${stack_name}";

    aws cloudformation wait change-set-create-complete ${change_set_params} ${stack_params}

    if [[ "$?" -ne "0" ]]; then
        echo "Perhaps no changes to apply, exiting"
        aws cloudformation delete-change-set --change-set-name=${change_set_arn} &> /dev/null
        exit 0
    fi

    echo "Change set ${change_set_name} created for stack ${stack_name}";

    stack_template=$(aws cloudformation get-template --stack-name ${stack_name} | jq -S .)
    change_set_template=$(aws cloudformation get-template --change-set-name ${change_set_name} --stack-name ${stack_name} | jq -S .)
    template_diff=$(diff --suppress-common-lines -u <(echo "${stack_template}") <(echo "${change_set_template}"))

    stack_parameters=$(aws cloudformation describe-stacks --stack-name ${stack_name} |
    jq -S '.Stacks[0].Parameters |= sort_by(.ParameterKey) | .Stacks[0].Parameters[]')
    change_set_parameters=$(aws cloudformation describe-change-set --change-set-name ${change_set_name} --stack-name ${stack_name} |
     jq -S '.Parameters |= sort_by(.ParameterKey) | .Parameters[]')
    parameter_diff=$(diff --suppress-common-lines -u <(echo "${stack_parameters}") <(echo "${change_set_parameters}"))

    echo "Applying the following changes:"

    if [[ "$template_diff" != "" ]]; then
        echo "Template:"
        echo ${template_diff}
    fi

    if [[ "$template_diff" != "" ]]; then
        echo "Parameters:"
        echo ${parameter_diff}
    fi

    aws cloudformation execute-change-set --change-set-name ${change_set_arn}

    aws cloudformation wait stack-update-complete ${stack_params}
    if [[ "$?" -ne 0 ]]; then
        echo "ERROR: Failed to update ${stack_name} with change set ${change_set_name}";
        exit 1;
    fi
fi

echo "Successfully created stack ${stack_name}";
