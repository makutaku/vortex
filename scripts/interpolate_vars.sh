#!/bin/bash

# Check the number of arguments provided
if [[ "$#" -lt 1 ]]; then
    echo "Usage: $0 <input_env_file> [output_env_file]" >&2
    exit 1
fi

input_file="$1"
input_filename=$(basename "$input_file")

# Determine the output file based on the number of arguments
if [[ "$#" -eq 1 ]]; then
    if [[ "$input_filename" == .* ]]; then
        echo "Error: Auto-generated hidden output filename not possible as input filename starts with '.'. Please specify both input and output filenames." >&2
        exit 1
    else
        output_file="$(dirname "$input_file")/.$input_filename"
    fi
else
    output_file="$2"
fi

# Check if the input file exists
if [ ! -f "$input_file" ]; then
    echo "Error: Input file does not exist." >&2
    exit 1
fi

declare -A vars
declare -a processed_lines
line_number=0

# Read and process the input file
while IFS= read -r line || [[ -n "$line" ]]; do
    ((line_number++))
    # Preserve comments and empty lines
    if [[ "$line" =~ ^# ]] || [[ -z "$line" ]]; then
        processed_lines+=("$line")
        #echo "$line"
        continue
    fi

    # Support both 'key=value' and 'key: value' formats
    if ! [[ "$line" =~ ^([a-zA-Z_][a-zA-Z0-9_]*)[:=]\s*(.*) ]]; then
        echo "Invalid line format: $line" >&2
        continue
    fi

    key="${BASH_REMATCH[1]}"
    value="${BASH_REMATCH[2]}"

    # Function to resolve variable references and evaluate expressions
    function resolve_and_evaluate {
        local var_value="$1"
        # Replace variables ${VAR} or $VAR, respecting quotes
        while [[ "$var_value" =~ (\$\{?([a-zA-Z_][a-zA-Z0-9_]*)\}?) ]]; do
            local full_match="${BASH_REMATCH[1]}"
            local var_name="${BASH_REMATCH[2]}"
            local replacement="${vars[$var_name]:-${!var_name}}"
            if [ -z "$replacement" ]; then
                echo "Error: Unresolved variable \${$var_name} on line $line_number." >&2
                exit 1
            fi
            # Remove enclosing quotes from the replacement if necessary
            replacement="${replacement%\'*}"
            replacement="${replacement#\'*}"
            replacement="${replacement%\"*}"
            replacement="${replacement#\"*}"
            # Replace the first occurrence
            var_value="${var_value//"$full_match"/"$replacement"}"
        done

        # Evaluate Bash expressions $(...)
        while [[ "$var_value" =~ \$(\(.*\)) ]]; do
            local expr="${BASH_REMATCH[1]}"
            local result=$(eval "$expr")
            if [ $? -ne 0 ]; then
                echo "Error evaluating expression '$expr' on line $line_number." >&2
                exit 1
            fi
            # Replace the evaluated expression
            var_value="${var_value//"$BASH_REMATCH"/"$result"}"
        done

        echo "$var_value"
    }

    resolved_value=$(resolve_and_evaluate "$value")
    if [ $? -ne 0 ]; then
        exit 1  # Ensure that the script exits if resolve_and_evaluate encounters an error
    fi
    vars["$key"]="$resolved_value"
    processed_lines+=("$key=$resolved_value")
    #echo "$key=$resolved_value"  # Echo for output to terminal
done < "$input_file"

# Write the processed lines to the output file
printf "%s\n" "${processed_lines[@]}" > "$output_file"
